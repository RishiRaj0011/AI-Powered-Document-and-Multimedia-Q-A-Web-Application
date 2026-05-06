import { createContext, useContext } from "react";

const PlayerContext = createContext(null);

export function PlayerProvider({ children, playerRef }) {
  return (
    <PlayerContext.Provider value={playerRef}>
      {children}
    </PlayerContext.Provider>
  );
}

export function usePlayer() {
  const context = useContext(PlayerContext);
  if (context === undefined) {
    throw new Error("usePlayer must be used within a PlayerProvider");
  }
  return context;
}
