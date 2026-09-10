# 100 uppdateringar och småfixar — Image Draw Bot 1.0.133-rc1

Jämförelsebas: den tidigare levererade 1.0.132-rc1. Nedan räknas konkreta
beteendeändringar i koden; testfall, versionsbyten och dokumentation räknas inte
som extra uppdateringar. Sammanhängande rättningar kan dela kod och testfall.

Prioritering: korrekt ritplan och stabil körning först, därefter återupptagning,
profiler, förhandsvisning och tydliga felmeddelanden.

| Område | Antal |
| --- | ---: |
| Färger | 12 |
| Lagring | 5 |
| Tidsbudget | 6 |
| Ritplan | 2 |
| Förhandsvisning | 17 |
| Bildinläsning | 1 |
| Planering | 5 |
| Användarflöde | 10 |
| Återupptagning | 10 |
| Tidsuppskattning | 6 |
| Profiler | 12 |
| Precision | 4 |
| Körning | 10 |
| **Totalt** | **100** |

## Ändringar

1. **Färger — `ColorCache.py`:** Trasigt schema i färgcachen ger tom cache i stället för krasch.
2. **Färger — `ColorCache.py`:** Begränsar läsning av färgcache till 1 MB.
3. **Färger — `ColorCache.py`:** Kräver kompletta RGB-tripletter inom 0–255.
4. **Färger — `ColorCache.py`:** Avvisar ogiltiga och icke ändliga verifieringsmått.
5. **Färger — `ColorCache.py`:** Kontrollerar att färgnyckeln motsvarar begärd RGB.
6. **Färger — `ColorCache.py`:** Kontrollerar verifiering och kalibreringskontext för varje post.
7. **Färger — `ColorCache.py`:** Begränsar även inlästa och direkt sparade cacher till 256 färger.
8. **Färger — `ColorCache.py`:** Förnyad verifiering flyttar färgen sist i utkastningsordningen.
9. **Färger — `ColorCache.py`:** Sparar färgcachen med gemensam atomisk skrivning och flush till disk.
10. **Färger — `ColorCache.py`:** Låser samtidiga färgcacheuppdateringar för att undvika förlorade poster.
11. **Lagring — `RuntimePaths.py`:** Tom LOCALAPPDATA använder hemkatalogen i paketerade byggen.
12. **Lagring — `RuntimePaths.py`:** Rensar temporär fil även när kodning eller skrivning misslyckas.
13. **Tidsbudget — `TimeBudgetEngine.py`:** Automatisk reserv avvisar oändliga och negativa tidsgränser.
14. **Tidsbudget — `TimeBudgetEngine.py`:** Normaliserar blanksteg runt tidslägets namn.
15. **Tidsbudget — `TimeBudgetEngine.py`:** Fasta och obegränsade lägen blockeras inte av ett gammalt manuellt gränsvärde.
16. **Tidsbudget — `TimeBudgetEngine.py`:** Respekterar numerisk noll som uttryckligt avstängd reserv.
17. **Tidsbudget — `TimeBudgetEngine.py`:** Ogiltig ETA kan inte klassas som säker.
18. **Tidsbudget — `TimeBudgetEngine.py`:** Ogiltig aktiv budget klassas konservativt som PANIC.
19. **Ritplan — `TimeBudget.py`:** Unlimited / Accuracy får inte längre automatisk gräns för antalet banor.
20. **Ritplan — `TimeBudget.py`:** Väljer begränsade banor med partiell sortering för stora planer.
21. **Förhandsvisning — `PreviewLayers.py`:** Använder uppåtrundning så provtagningen håller gränsen för segment.
22. **Förhandsvisning — `PreviewLayers.py`:** Provtagning begränsar även stora punktplaner.
23. **Förhandsvisning — `PreviewLayers.py`:** Skalar ned källbilden före RGB-konvertering för lägre minnesåtgång.
24. **Förhandsvisning — `PreviewLayers.py`:** Visar transparenta pixlar mot vit bakgrund i färg- och fyllnadskartor.
25. **Förhandsvisning — `PreviewLayers.py`:** Tar bort onödig ljusstyrkekopia utan visuell effekt.
26. **Förhandsvisning — `PreviewLayers.py`:** Fyllnadskant fungerar även för bilder på en eller två pixlar.
27. **Förhandsvisning — `PreviewLayers.py`:** Fyllnadsförhandsvisning kan avbrytas mellan regioner.
28. **Förhandsvisning — `PreviewSafety.py`:** Tomma säkerhetsbanor hoppas över utan indexfel.
29. **Förhandsvisning — `PreviewSafety.py`:** Säkerhetskartans avbrytknapp kontrolleras mellan banor.
30. **Förhandsvisning — `PreviewSafety.py`:** Kontrollerar avbrott även inuti mycket långa förhandsvisningsbanor.
31. **Förhandsvisning — `PreviewSafety.py`:** Små säkerhetskartor kraschar inte vid ritning av etiketter.
32. **Förhandsvisning — `PreviewSafety.py`:** Exporterad säkerhetsmetadata delar inte längre muterbara objekt med planen.
33. **Förhandsvisning — `PreviewQuality.py`:** Ogiltig sparad RAM-budget återgår till 512 MB.
34. **Förhandsvisning — `PreviewQuality.py`:** Full förhandsvisning bevarar skärmområdet för absoluta säkerhetspolygoner.
35. **Förhandsvisning — `PreviewQuality.py`:** Tom källbild ger ett tydligt fel före division.
36. **Förhandsvisning — `PreviewQuality.py`:** Ogiltig zoom återgår till anpassa bild.
37. **Förhandsvisning — `PreviewQuality.py`:** Ogiltig panorering återcentrerar bilden.
38. **Bildinläsning — `ImageFormatInfo.py`:** Bildetiketten undviker full RGBA-kopia för opaka bilder och bilder med separat alfakanal.
39. **Färger — `ColorPreviewDiagnostics.py`:** Ogiltiga färgmätningar märks Unavailable i stället för missvisande kvalitetsbetyg.
40. **Färger — `ColorPreviewDiagnostics.py`:** Automatisk ommappning tolererar trasig diagnostik utan krasch eller strängtolkad flagga.
41. **Planering — `PlanningWatchdog.py`:** Överflödande numeriska inställningar återgår till reservvärden i watchdog.
42. **Planering — `PlanningWatchdog.py`:** Icke ändlig planeringstid använder normal tidsgräns.
43. **Planering — `PlanningWatchdog.py`:** Snabb torrkörning stänger även av regionfyllnadsmotorn.
44. **Planering — `PlanningWatchdog.py`:** Sista reservplanen stänger verkligen av regionfyllnad.
45. **Planering — `PlanningWatchdog.py`:** Obegränsat noggrannhetsläge bevarar färgval och bangränser vid reservplanering.
46. **Användarflöde — `UIState.py`:** En vald målprofil krävs innan arbetsytan visar redo för test.
47. **Användarflöde — `UIState.py`:** Pågående arbete visas före ett gammalt felmeddelande.
48. **Användarflöde — `UIState.py`:** Tidsgränsfel känns igen även utan prefixet Error.
49. **Användarflöde — `UIState.py`:** Start locked känns igen och visar stegen för upplåsning.
50. **Användarflöde — `UIState.py`:** GPU-fel får GPU-råd även när meddelandet nämner färgmappning.
51. **Användarflöde — `UIState.py`:** Disk full ger konkret råd om att frigöra utrymme.
52. **Användarflöde — `UIState.py`:** Skrivskydd ger råd om skrivbar mapp och fillås.
53. **Användarflöde — `UIState.py`:** Oläsbara bildformat ger ett begripligt återställningsråd.
54. **Användarflöde — `UIState.py`:** Saknade Python-komponenter får installationsråd.
55. **Användarflöde — `UIState.py`:** Minnesbrist ger råd om mindre bildyta och förhandsvisning.
56. **Återupptagning — `RenderResume.py`:** Dubblerade färgindex skapar inte dubbla återupptagningsbatcher.
57. **Återupptagning — `RenderResume.py`:** Återupptagning kan identifiera planer som endast har execution_groups.
58. **Återupptagning — `RenderResume.py`:** Negativa batchindex avvisas före Python-indexering.
59. **Återupptagning — `RenderResume.py`:** Planens fingeravtryck inkluderar alfakanalen.
60. **Återupptagning — `RenderResume.py`:** Hashar plangeometri stegvis utan en jättestor JSON-sträng.
61. **Återupptagning — `RenderResume.py`:** Kontrollerar att sparade fingeravtryck är riktiga hexvärden.
62. **Återupptagning — `RenderResume.py`:** Ogiltiga antal och negativa banpositioner avvisas i stället för att klampas.
63. **Återupptagning — `RenderResume.py`:** Sparade booleska flaggor måste vara booleska värden.
64. **Återupptagning — `RenderResume.py`:** Kontrollerar längd, format och unika nycklar för avslutade färgbatcher.
65. **Återupptagning — `RenderResume.py`:** Nya bankontrollpunkter måste motsvara verkligt antal ordnade banor.
66. **Tidsuppskattning — `HybridCostModel.py`:** Trasiga räknare i operationshistoriken hoppas över.
67. **Tidsuppskattning — `HybridCostModel.py`:** Felaktig kalibreringsstruktur återgår till standardkostnader.
68. **Tidsuppskattning — `HybridCostModel.py`:** Ogiltigt antal kalibreringsprov kan inte krascha modellbyggandet.
69. **Tidsuppskattning — `HybridCostModel.py`:** Punktkostnad använder uppmätta punktoperationer när de finns.
70. **Tidsuppskattning — `HybridCostModel.py`:** Distansbaserad bankostnad respekterar det inlärda kostnadsgolvet.
71. **Tidsuppskattning — `HybridCostModel.py`:** Avvisar ogiltiga distanser som annars gav optimistisk bankostnad.
72. **Profiler — `ProfilePortability.py`:** Profilimport och export avvisar NaN och Infinity.
73. **Profiler — `ProfilePortability.py`:** Läser UTF-8-profiler med BOM från Windows-redigerare.
74. **Profiler — `ProfilePortability.py`:** Begränsar faktisk filläsning även om filen växer efter storlekskontrollen.
75. **Profiler — `ProfilePortability.py`:** Dubbla JSON-nycklar ger fel i stället för tyst överskrivning.
76. **Profiler — `ProfilePortability.py`:** Extremt nästlade profiler fångas före kopiering och ger begripligt fel.
77. **Profiler — `ProfilePortability.py`:** Avvisar okända inställningssektioner i importerade profiler.
78. **Profiler — `ProfilePortability.py`:** Tomma listor godtas inte längre som objektsektioner.
79. **Profiler — `ProfilePortability.py`:** Canvas med noll bredd eller höjd avvisas vid import.
80. **Profiler — `ProfilePortability.py`:** Namnförslag för importerade kopior undviker kollisioner oavsett skiftläge.
81. **Profiler — `ProfilePortability.py`:** Långa profilnamn får ett giltigt första kopienamn inom 50 tecken.
82. **Profiler — `ProfilePortability.py`:** Profilimport blockeras under pågående ritning eller planering.
83. **Profiler — `ProfilePortability.py`:** Misslyckad sparning av aktuell profil avbryter importen utan tyst dataförlust.
84. **Precision — `Precision.py`:** Precisionens profilvärden kan inte ändras genom en returnerad referens.
85. **Precision — `Precision.py`:** Avvisar icke ändliga pixelkoordinater före skärmtransformering.
86. **Precision — `Precision.py`:** CanvasTransform validerar storlek och skärmursprung redan vid skapandet.
87. **Precision — `Precision.py`:** Felaktig steglängd använder samma reservvärde som icke ändlig steglängd.
88. **Lagring — `ProfileStorage.py`:** Sanerade eller avkortade profilnycklar får hashändelse som undviker filkollisioner.
89. **Lagring — `ProfileStorage.py`:** Längdmärker extra kalibreringskontext för att undvika tvetydiga radbrytningar.
90. **Lagring — `ProfileStorage.py`:** Hashar kalibreringsfiler i block med begränsad minnesåtgång.
91. **Körning — `DeadlineScheduler.py`:** Schemaläggaren tar en kopia av operationsmetadata vid skapandet.
92. **Körning — `DeadlineScheduler.py`:** Ogiltig starttid eller budget stoppas före schemaläggning.
93. **Körning — `DeadlineScheduler.py`:** Trasiga eller negativa operationskostnader kan inte tolkas som gratis arbete.
94. **Körning — `DeadlineScheduler.py`:** Struktur- och betydelsevärden normaliseras till ändliga värden inom 0–1.
95. **Körning — `DeadlineScheduler.py`:** Uttrycklig betydelse noll bevaras i prioriteringen.
96. **Körning — `DeadlineScheduler.py`:** Icke ändliga klockvärden stoppas med ett tydligt fel.
97. **Körning — `DeadlineScheduler.py`:** Avslutad tidsmätning nollställs så den inte återanvänds för nästa operation.
98. **Körning — `DeadlineScheduler.py`:** Operationer utan startmätning förorenar inte inlärd ritfart.
99. **Körning — `DeadlineScheduler.py`:** Skiljer tidsbrist från lågprioriterat arbete i räknaren för bortval.
100. **Körning — `DeadlineScheduler.py`:** Diagnostik visar antal överhoppade operationer per orsak.

## Verifiering

Alla ändrade moduler omfattas av nya eller befintliga tester. De 51 nya
regressionstesterna finns i `test_hundred_improvements.py`; flera prövar flera
felvärden eller kombinationer. Befintliga tester provar även integrationen med
ritmotorn och simulerad mus. Se `VALIDATION-v1.0.133-rc1.md` för slutresultatet.

## Kompatibilitet

- Äldre ritkontrollpunkter får ett annat bildfingeravtryck efter ändringen till
  RGBA. De återupptas inte genom att hoppa över tidigare banor; skapa en ny plan.
- Felaktiga färgcacheposter ignoreras och måste verifieras på nytt.
- Profilnycklar med specialtecken eller över 80 tecken får nya filnamn för att
  undvika kollisioner. Standardprofiler och vanliga genererade custom-nycklar
  behåller sina filnamn. Äldre filer raderas inte.
- Profiler med dubbla JSON-nycklar, icke ändliga värden eller tom canvas avvisas.
- Denna omgång bygger vidare på tidigare funktioner. Den implementerar inte
  generell återupptagning av progressiva pass, dirty-tile-omplanering eller fysisk
  kalibrering av penselform.
- GitHub har inte uppdaterats. Fysisk Windows-/GPU-verifiering återstår.
