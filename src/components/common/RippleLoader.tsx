
export default function RippleLoader() {
  return (
    <div className="relative h-62.5 w-62.5">
      <style>{`
        @keyframes ripple-spin-cw {
          0% { transform: scale(1) rotate(0deg); opacity: 0.9 }
          25% { transform: scale(1.2) rotate(90deg); opacity: 0.3 }
          50% { transform: scale(1.35) rotate(180deg); opacity: 0.6 }
          75% { transform: scale(1.2) rotate(270deg); opacity: 0.8 }
          100% { transform: scale(1) rotate(360deg); opacity: 0.9 }
        }
        @keyframes ripple-spin-ccw {
          0% { transform: scale(1) rotate(0deg); opacity: 0.9 }
          25% { transform: scale(1.2) rotate(-90deg); opacity: 0.3 }
          50% { transform: scale(1.35) rotate(-180deg); opacity: 0.6 }
          75% { transform: scale(1.2) rotate(-270deg); opacity: 0.8 }
          100% { transform: scale(1) rotate(-360deg); opacity: 0.9 }
        }
      `}</style>

      <div className="absolute inset-0 flex items-center justify-center z-100 text-white font-extrabold select-none">
        WC3
      </div>

      <div style={{ animationDelay: "0s" }} className={`absolute inset-[42%] z-99 rounded-[40%] border-t border-gray-500 backdrop-blur-sm bg-linear-to-b from-gray-500/25 to-gray-700/25 animate-[ripple-spin-cw_2.5s_ease-in-out_infinite]`} />
      <div style={{ animationDelay: "0.2s" }} className={`absolute inset-[32%] z-98 rounded-[40%] border-t border-gray-400 backdrop-blur-sm bg-linear-to-b from-gray-400/22 to-gray-600/22 animate-[ripple-spin-ccw_3s_ease-in-out_infinite]`} />
      <div style={{ animationDelay: "0.4s" }} className={`absolute inset-[22%] z-97 rounded-[40%] border-t border-gray-300 backdrop-blur-sm bg-linear-to-b from-gray-300/20 to-gray-500/20 animate-[ripple-spin-cw_3.5s_ease-in-out_infinite]`} />
      <div style={{ animationDelay: "0.6s" }} className={`absolute inset-[12%] z-96 rounded-[40%] border-t border-gray-200 backdrop-blur-sm bg-linear-to-b from-gray-200/18 to-gray-400/18 animate-[ripple-spin-ccw_4s_ease-in-out_infinite] shadow-2xl`} />
    </div>
  )
}
