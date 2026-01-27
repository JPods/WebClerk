
export default function RippleLoader() {
  return (
    <div className="relative h-62.5 w-62.5">
      <style>{`
        @keyframes ripple-spin-cw {
          0% { transform: scale(1) rotate(0deg); opacity: 0.9 }
          50% { transform: scale(1.35) rotate(180deg); opacity: 0.6 }
          100% { transform: scale(1) rotate(360deg); opacity: 0.9 }
        }
        @keyframes ripple-spin-ccw {
          0% { transform: scale(1) rotate(0deg); opacity: 0.9 }
          50% { transform: scale(1.35) rotate(-180deg); opacity: 0.6 }
          100% { transform: scale(1) rotate(-360deg); opacity: 0.9 }
        }
      `}</style>

      <div style={{ animationDelay: "0s" }} className="absolute inset-[40%] z-99 rounded-full border-t border-emerald-500 backdrop-blur-sm bg-linear-to-b from-emerald-500/20 to-emerald-700/20 animate-[ripple-spin-cw_2.5s_ease-in-out_infinite]" />
      <div style={{ animationDelay: "0.2s" }} className="absolute inset-[30%] z-98 rounded-full border-t border-emerald-400 backdrop-blur-sm bg-linear-to-b from-emerald-500/20 to-emerald-700/20 animate-[ripple-spin-ccw_3s_ease-in-out_infinite]" />
      <div style={{ animationDelay: "0.4s" }} className="absolute inset-[20%] z-97 rounded-full border-t border-emerald-300 backdrop-blur-sm bg-linear-to-b from-emerald-500/20 to-emerald-700/20 animate-[ripple-spin-cw_3.5s_ease-in-out_infinite]" />
      <div style={{ animationDelay: "0.6s" }} className="absolute inset-[10%] z-96 rounded-full shadow-2xl border-t border-emerald-200 backdrop-blur-sm bg-linear-to-b from-emerald-500/20 to-emerald-700/20 animate-[ripple-spin-ccw_4s_ease-in-out_infinite]" />
    </div>
  )
}
