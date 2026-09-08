# Bildformat

Formatet läses från bildens innehåll, inte filändelsen. PNG, JPEG, WebP och BMP har testats. Appen visar format, bredd × höjd och om bilden faktiskt innehåller transparenta pixlar. PNG betyder inte automatiskt att bakgrunden är transparent.

Filer, filsläpp och nedladdade bild-URL:er använder samma bildläsare. Inklistrade bildpixlar visas som Clipboard / decoded pixels om originalformatet saknas. En ny inklistrad bild nollställer också föregående motivruta.

5 nya formattester och 12 motivtester passerar. Windows-gränssnittet är inte verifierat här. Starta med Start.bat efter att hela ZIP-filen packats upp.
