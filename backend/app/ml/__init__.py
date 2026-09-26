"""DoriIshonch AI moduli — oʻz modellarimiz.

1. risk_model — skan xavf modeli (gradient boosting). Har bir skanerlash uchun "qalbaki boʻlish ehtimoli"
   va uning sabablari. Qoidalar xulosasini oʻzgartirmaydi: bu qoʻshimcha signal (CLAUDE.md qoidasi).
2. packnet — qadoq surati modeli (kichik CNN). Suratdagi quti qaysi dori qadogʻiga oʻxshashini va
   asl dizayndan farq bor-yoʻqligini baholaydi. Ayni oʻsha ogʻirliklar serverda (numpy), brauzerda va
   iPhone da (TypeScript) ishlaydi.

Claude (services/ai.py) faqat tushuntirish va matn oʻqish uchun; xavf bahosini oʻz modellarimiz beradi.
"""
