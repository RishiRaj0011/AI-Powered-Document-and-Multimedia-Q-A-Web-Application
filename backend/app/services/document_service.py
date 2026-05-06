import os
import uuid
import time
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from openai import AsyncOpenAI
from app.core.config import settings
from app.repositories.document_repository import DocumentRepository
from app.models.document import DocumentStatus, DocumentType
from app.schemas.document import DocumentResponse

EXTENSION_TYPE_MAP = {
    "pdf": DocumentType.PDF,
    "docx": DocumentType.DOCX,
    "txt": DocumentType.TXT,
    "mp3": DocumentType.AUDIO,
    "wav": DocumentType.AUDIO,
    "m4a": DocumentType.AUDIO,
    "mp4": DocumentType.VIDEO,
}


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.repo = DocumentRepository(db)
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX_NAME)
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    async def upload(self, file: UploadFile, owner_id: int) -> DocumentResponse:
        ext = Path(file.filename).suffix.lstrip(".").lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File type .{ext} not allowed")

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

        safe_filename = f"{uuid.uuid4()}.{ext}"
        save_path = Path(settings.UPLOAD_DIR) / safe_filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(content)

        doc = await self.repo.create(
            owner_id=owner_id,
            filename=safe_filename,
            original_filename=file.filename,
            file_size=len(content),
            doc_type=EXTENSION_TYPE_MAP.get(ext, DocumentType.TXT),
        )
        return DocumentResponse.model_validate(doc)

    async def process(self, doc_id: int, owner_id: int):
        doc = await self.repo.get_by_id(doc_id, owner_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        await self.repo.update_status(doc_id, DocumentStatus.PROCESSING)
        try:
            file_path = str(Path(settings.UPLOAD_DIR) / doc.filename)
            texts = await self._extract_text(file_path, doc.doc_type)
            chunks = self.splitter.split_documents(texts)
            namespace = f"user-{owner_id}-doc-{doc_id}"
            await self._upsert_chunks(chunks, namespace, doc_id)
            await self.repo.update_status(doc_id, DocumentStatus.READY, len(chunks), namespace)
        except Exception as e:
            await self.repo.update_status(doc_id, DocumentStatus.FAILED, error=str(e))
            raise

    async def _extract_text(self, file_path: str, doc_type: DocumentType):
        if doc_type == DocumentType.PDF:
            loader = PyPDFLoader(file_path)
        elif doc_type == DocumentType.DOCX:
            loader = Docx2txtLoader(file_path)
        elif doc_type in (DocumentType.AUDIO, DocumentType.VIDEO):
            transcript = await self._transcribe(file_path)
            from langchain.schema import Document as LCDoc
            return [LCDoc(page_content=transcript, metadata={"source": file_path})]
        else:
            loader = TextLoader(file_path)
        return loader.load()

    async def _transcribe(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1", file=f
            )
        return response.text

    async def _upsert_chunks(self, chunks, namespace: str, doc_id: int):
        texts = [c.page_content for c in chunks]
        embeddings = await self.embeddings.aembed_documents(texts)
        vectors = [
            {
                "id": f"{doc_id}-{i}",
                "values": emb,
                "metadata": {"doc_id": doc_id, "text": texts[i], **chunks[i].metadata},
            }
            for i, emb in enumerate(embeddings)
        ]
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i:i + batch_size], namespace=namespace)

    async def list_documents(self, owner_id: int, skip: int = 0, limit: int = 20):
        docs, total = await self.repo.list_by_owner(owner_id, skip, limit)
        return {"items": [DocumentResponse.model_validate(d) for d in docs], "total": total}

    async def delete(self, doc_id: int, owner_id: int):
        doc = await self.repo.get_by_id(doc_id, owner_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.pinecone_namespace:
            self.index.delete(delete_all=True, namespace=doc.pinecone_namespace)
        await self.repo.delete(doc_id, owner_id)
