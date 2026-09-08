# Skala upp en liten bild

1. Lägg in bilden som vanligt.
2. Under **Add image**, klicka **Upscale image…**.
3. Välj **2×** eller **4×**. Dialogen visar bildstorleken före och efter samt ett förslag för små bilder.
4. Välj **Smooth** för foton/illustrationer eller **Pixel art** för tydliga pixelblock.
5. Klicka **Upscale image**, därefter **Build preview**. **Undo** ångrar det senaste uppskalningssteget.

Uppskalningen startar inte ritning. Väntande automatisk ritstart avaktiveras när uppskalningsdialogen öppnas eller Undo används. Förhandsvisningen behöver byggas igen; gamla återupptagningspunkter för ritning tas bort. En ny importerad bild nollställer Undo. Din motivruta använder relativa koordinater och behålls vid uppskalning.

Detta är vanlig bildskalning med Lanczos eller nearest-neighbour, utan AI. Den återställer inte saknade ansiktsdetaljer och kan inte reparera en kraftigt suddig bild. Transparens bevaras, och Smooth hanterar alfa för att undvika färgkanter från osynliga pixlar. Resultatet får vara högst 25 megapixlar. Esc/Stop kan avbryta före skalningen eller hindra att resultatet används efter skalningen; själva Pillow-anropet kan inte avbrytas mitt i.

Ritytan bestämmer fortfarande slutlig ritstorlek. Den befintliga ritmotorn skalar redan bilden till ritytan; detta är ett extra redigeringssteg, inte ett krav för små bilder. Upprepad skalning kan göra bilden mjukare, så börja hellre från originalet.

9 nya tester verifierar dimensioner, storleksgräns, transparens, pixelart, avbrott, metadata och att resultathändelsen inte köar automatisk ritning. Windows-gränssnitt och faktisk musritning är inte verifierade här.
