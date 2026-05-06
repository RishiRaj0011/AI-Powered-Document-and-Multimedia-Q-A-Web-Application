import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { Loader } from "lucide-react";

function validate(email, password, confirm) {
  const errors = {};
  if (!email) errors.email = "Email is required";
  if (password.length < 8) errors.password = "Password must be at least 8 characters";
  else if (!/[A-Z]/.test(password)) errors.password = "Password must contain at least one uppercase letter";
  else if (!/[0-9]/.test(password)) errors.password = "Password must contain at least one number";
  if (password !== confirm) errors.confirm = "Passwords do not match";
  return errors;
}

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fullName, setFullName] = useState("");
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError("");
    const fieldErrors = validate(email, password, confirm);
    if (Object.keys(fieldErrors).length) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      await register(email, password, fullName || undefined);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setApiError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : "Registration failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const field = (label, id, type, value, onChange, error, placeholder, autoComplete) => (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <input
        id={id}
        className={`input-field ${error ? "border-red-400 focus:ring-red-400" : ""}`}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="card w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-600">DocQA</h1>
          <p className="text-gray-500 mt-1 text-sm">AI-powered document assistant</p>
        </div>

        <h2 className="text-xl font-semibold text-gray-900 mb-6">Create account</h2>

        {apiError && (
          <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {field("Full Name (optional)", "fullName", "text", fullName, setFullName, null, "Jane Doe", "name")}
          {field("Email", "email", "email", email, setEmail, errors.email, "you@example.com", "email")}
          {field("Password", "password", "password", password, setPassword, errors.password, "Min 8 chars, 1 uppercase, 1 number", "new-password")}
          {field("Confirm Password", "confirm", "password", confirm, setConfirm, errors.confirm, "Repeat password", "new-password")}

          <button
            className="btn-primary w-full flex items-center justify-center gap-2"
            type="submit"
            disabled={loading}
          >
            {loading && <Loader size={16} className="animate-spin" />}
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-gray-600">
          Already have an account?{" "}
          <Link to="/login" className="text-primary-600 hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
