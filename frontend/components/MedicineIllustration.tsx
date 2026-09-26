export function MedicineIllustration() {
  return <svg className="medicine-illustration" viewBox="0 0 440 360" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id="box-face" x1="158" y1="95" x2="340" y2="305" gradientUnits="userSpaceOnUse"><stop stopColor="#fff" /><stop offset="1" stopColor="#eef4e9" /></linearGradient>
      <linearGradient id="box-side" x1="324" y1="111" x2="379" y2="300" gradientUnits="userSpaceOnUse"><stop stopColor="#d9e8d2" /><stop offset="1" stopColor="#b4cba9" /></linearGradient>
      <filter id="box-shadow" x="-40%" y="-30%" width="180%" height="180%"><feDropShadow dx="0" dy="18" stdDeviation="16" floodColor="#244c36" floodOpacity=".13" /></filter>
    </defs>
    <circle cx="239" cy="180" r="136" fill="#dceacf" /><circle cx="239" cy="180" r="108" stroke="#bfd2b1" strokeDasharray="3 9" /><ellipse cx="244" cy="308" rx="119" ry="16" fill="#bfd0b1" fillOpacity=".4" />
    <g filter="url(#box-shadow)" transform="rotate(-9 228 191)">
      <path d="m145 108 154-9 48 28-154 10-48-29Z" fill="#fff" /><path d="m299 99 48 28v164l-48-28V99Z" fill="url(#box-side)" /><path d="m145 108 154-9v164l-154 9V108Z" fill="url(#box-face)" />
      <path d="m145 132 154-9v36l-154 9v-36Z" fill="#246449" /><path d="m299 123 48 28v36l-48-28v-36Z" fill="#194f39" /><path d="M164 145h55" stroke="#eaf4db" strokeWidth="5" strokeLinecap="round" />
      <text x="164" y="193" fill="#283d30" fontSize="17" fontFamily="Manrope, sans-serif" fontWeight="800">Dori qutisi</text><path d="M164 210h60m-60 10h43" stroke="#bac6b5" strokeWidth="4" strokeLinecap="round" /><rect x="249" y="181" width="33" height="33" rx="2" fill="#e3ebdd" /><path d="M254 186h7v7h-7zm15 0h7v7h-7zm-15 15h7v7h-7zm14-2h3v3h-3zm5 5h4v4h-4z" fill="#345640" /><path d="M164 249h78" stroke="#bcc7b5" strokeWidth="4" strokeLinecap="round" />
    </g>
    <g transform="rotate(13 142 245)" filter="url(#box-shadow)"><rect x="94" y="211" width="86" height="94" rx="15" fill="#f7f8f1" /><rect x="102" y="221" width="70" height="72" rx="9" fill="#dfe7d8" />{[0, 1, 2].map(row => [0, 1].map(column => <g key={`${row}-${column}`} transform={`translate(${113 + column * 30} ${230 + row * 22})`}><rect width="17" height="12" rx="6" fill="#fbfcf8" /><path d="M8.5 1v10" stroke="#dce5d3" /></g>))}</g>
    <g filter="url(#box-shadow)"><rect x="236" y="259" width="158" height="51" rx="14" fill="white" /><circle cx="260" cy="285" r="14" fill="#e6f1dc" /><path d="m254 285 4 4 8-9" stroke="#346142" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /><text x="282" y="290" fill="#304331" fontSize="13" fontWeight="700" fontFamily="Manrope, sans-serif">Qutini tekshiring</text></g>
    <rect x="324" y="60" width="58" height="58" rx="19" fill="white" transform="rotate(9 324 60)" /><path d="m350 76 13 5v9c0 6-6 11-13 14-7-3-13-8-13-14v-9l13-5Z" fill="#d9ebc5" /><path d="m344 89 4 4 8-9" stroke="#386a45" strokeWidth="2.5" strokeLinecap="round" /><path d="M105 106v14m-7-7h14M366 217v12m-6-6h12" stroke="#7e9b6f" strokeWidth="2.5" strokeLinecap="round" /><circle cx="146" cy="70" r="4" fill="#93ad7c" /><circle cx="398" cy="156" r="5" fill="#cedfb9" />
  </svg>;
}
