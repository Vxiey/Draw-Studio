# Börja med personerna och föremålen

1. Packa upp hela ZIP-filen och öppna **Start.bat**.
2. Lägg in bilden. Välj programmets profil och rityta som vanligt.
3. Under **Configure drawing → Subject focus** väljer du:
   - **Off:** rita som tidigare.
   - **Subject first:** rita det valda motivet först och bakgrunden sist. Med kort tid kan bakgrunden utelämnas.
   - **Subject only:** rita enbart det valda motivet.
4. Klicka **Mark subject…** och dra en ruta runt personerna eller sakerna. Klicka **Use selection**. Allt i rutan räknas som motiv, även bakgrund mellan personer.
5. **Check subject mask** visar motivet ljust och bakgrunden mörk. Den visar ett uppskattat urval, inte ett färdigt ritresultat.
6. Bygg ritförhandsvisningen. Använd **1 px penna** i målprogrammet och kontrollera färgkalibreringen. Kör ett litet test innan hela bilden.

**Auto** tar bort din markering. Då används bildens transparens, eller en uppskattning från en enkel, jämnfärgad bakgrund vid bildens kanter. En rörig bakgrund ger ett tydligt meddelande att du behöver markera motivet. Automatik kan missa hår, likfärgade kläder och föremål som går ihop med bakgrunden. En transparent PNG ger bättre kontroll över konturen.

Detta känner inte igen människor med AI. Markeringen kan omfatta flera personer eller vilket föremål som helst. Du kan använda en transparent PNG om du vill frilägga exakta konturer istället för en ruta.

Motivläget använder Pixel Accurate och planerar för 1 px penna. Det fungerar med full färgpalett, inte Outline, Eraser eller current-colour-only. Korrigeringspass är avstängda i motivläget så att avsiktligt utelämnad bakgrund inte återinförs. Grundbildens upplösning och palett behålls. Bakgrunden tas inte bort från en redan målad canvas: börja på en tom yta.

Läget börjar på Off när appen startas. En ny bild nollställer den gamla rutan. Att markera motiv eller visa masken startar ingen musritning. Dina befintliga start- och säkerhetsinställningar gäller fortfarande vid bildimport och Start.

## Verifiering

711 automatiserade tester godkända i Linux, inklusive 12 nya motivtester. Source self-test godkänd. Windows-gränssnitt, faktisk musritning, native dumpinsamling och riktig NVIDIA CUDA är inte verifierade i denna miljö. ZIP-filen innehåller källkod och Start.bat, inte en nybyggd Windows-EXE.

## Metodval

OpenCV dokumenterar interaktiv förgrundsavskiljning med GrabCut och behovet av rättningar när förgrund och bakgrund blandas: https://docs.opencv.org/4.10.0/d8/d83/tutorial_py_grabcut.html

Den här versionen använder istället rektangel, alfakanal eller deterministisk färgtröskel med sammanhängande bakgrund från bildkanterna. Inga nya ML- eller OpenCV-beroenden krävs. Automatisk mask uppskattas på högst 384 × 384 och skalas till ritbildens upplösning; kontrollera därför tunna detaljer.
