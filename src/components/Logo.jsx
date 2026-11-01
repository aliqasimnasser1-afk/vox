export default function Logo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="Vox">
      <rect width="32" height="32" rx="8" fill="#22c55e" />
      <path d="M8 9l8 15 8-15" stroke="#0f172a" strokeWidth="3.5" fill="none"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
