# Referanser i metocean-re (vindenergi)

Oversikt over kildene som brukes i `metocean_re/stats/`. For hver kilde står det
hva den brukes til, hvor den finnes, om den er sjekket, om den kan brukes, og
hvorfor vi har valgt akkurat den formelen.

Referansene står som tekst i docstringene i koden. Rettes en referanse her, må
den også rettes i koden (se kolonnen «Brukt i»).

## Status

| Merke | Betydning |
|---|---|
| ✅ | Bibliografiske data (forfattere, år, tidsskrift, volum, sider) er bekreftet via DOI (Crossref) |
| 🔶 | Kilden finnes, men innholdet (likning, tabell, avsnitt) er ikke sjekket mot originalteksten |
| ❓ | Usikker – kilden eller detaljene er ikke bekreftet |
| ⚠️ | Funnet noe som bør rettes eller formuleres annerledes |

Ingen likninger er ennå sjekket mot originalteksten. Det gjenstår (se [sjekklisten](#9-sjekkliste)).

### Kan referansene brukes?

- **Sitere og implementere formler er alltid lov.** Formler og metoder er ikke
  beskyttet av opphavsrett, så vi kan skrive dem i koden og henvise til kilden.
- **Standarder (IEC, ISO) er opphavsrettsbeskyttet tekst.** Vi kan henvise til
  dem og bruke verdiene, men ikke kopiere tekst eller hele tabeller inn i repoet.
- **Spørsmålet er derfor mest om kilden er god nok:** fagfellevurderte artikler,
  standarder og etablerte lærebøker er gode kilder. Konferanseartikler og notater
  er svakere og bør ha en sterkere kilde ved siden av, hvis det finnes en.

---

## 1. Vindprofil over rotoren (`profile.py`)

### IEC 61400-12-1 – rotor-ekvivalent vindhastighet (REWS)

- **Referanse:** IEC 61400-12-1:2017. *Wind energy generation systems – Part 12-1:
  Power performance measurements of electricity producing wind turbines.* Ed. 2.0.
- **Brukt i:** `profile.py: rotor_equivalent_wind_speed`, `wind_losses.py: wind_veer_loss`
- **Likning:** REWS = ( Σ A_i/A · (u_i cos Δφ_i)³ )^(1/3)
- **Hvorfor denne:** Effekten følger u³, så et vanlig gjennomsnitt av vinden over
  rotoren gir feil energi. REWS vekter hver stripe av rotoren med arealet sitt og
  bevarer den kinetiske energifluksen. Dette er den standardiserte definisjonen,
  også med vindvridning (cos Δφ).
- **Hvor:** Standard Norge (standard.no) / IEC webstore. Betalt, ofte tilgjengelig
  via universitetsbiblioteket (Standard Online).
- **Status:** 🔶 ⚠️ 2017-utgaven er **erstattet av IEC 61400-12-1:2022 (Ed. 3.0)**.
  Bestem hvilken utgave vi henviser til, og sjekk at nummereringen stemmer i den.
- **Kan brukes:** Ja, standarden er den beste kilden for REWS.

### Wagner et al. (2009)

- **Referanse:** Wagner, R., Antoniou, I., Pedersen, S. M., Courtney, M. S.,
  Jørgensen, H. E. (2009). The influence of the wind speed profile on wind turbine
  performance measurements. *Wind Energy* 12(4), 348–362.
  [doi:10.1002/we.297](https://doi.org/10.1002/we.297)
- **Brukt i:** `profile.py: rotor_equivalent_wind_speed`
- **Hvor i artikkelen** (ingen avsnittsnumre, så sidetall og likninger brukes):
  - Likn. (4)–(6), s. 351 (innledningen): tre definisjoner av «equivalent wind speed»
    - (4) U_eqM1 = Σ (A_i/A) U_i, vektet middel
    - (5) U_eqT1, som (4) med turbulensleddet fra likn. (3)
    - **(6) U_eqT3 = ( Σ (A_i/A) U_i³ )^(1/3)**, samme energifluks gjennom rotorarealet
  - Figur 2, s. 352: rotoren delt i horisontale segmenter (5 i figuren, 10 i simuleringene, s. 358)
  - S. 352: likn. (4)–(6) antar «zero tilt and yaw errors»
  - Sammendraget (s. 348) og konklusjonen (s. 362): effekten korrelerer klart
    bedre med den ekvivalente vindhastigheten enn med vinden i navhøyde
- **Sammenligning med koden:** Koden bruker likn. (6) uten turbulensleddet
  (turbulens behandles for seg i `turbulence.py`), med 20 horisontale striper.
  Formen stemmer.
  - Vindvridning (cos Δφ) er **ikke** med hos Wagner. Retning nevnes bare som
    videre arbeid (s. 361). Veer-delen må derfor henvise til IEC 61400-12-1.
  - Tilt: Wagner antar ingen tilt, og det gjør REWS i koden også. Tilt er et eget
    tap i `wind_losses.py: power_with_tilt` og kombineres ikke med REWS.
  - Merk (s. 358): i Wagners simuleringer passet likn. (4) best og likn. (6)
    dårligst. Forfatterne sier at dette avhenger av turbinkontrolleren (konstant
    turtall og pitch). Det er u³-formen, likn. (6), som er tatt inn i IEC
    61400-12-1, så IEC er hovedkilden for formelen og Wagner for ideen.
- **Hvorfor denne:** Originalartikkelen som viser at vind bare i navhøyde ikke er
  nok, og som foreslår en ekvivalent vindhastighet over hele rotoren.
  IEC-definisjonen bygger på dette arbeidet.
- **Hvor:** Wiley Online Library via UiB.
- **Status:** ✅ Sjekket mot artikkelen. Publisert på nett 2008, trykt i volum 12
  (2009), så 2009 er riktig å oppgi.
- **Kan brukes:** Ja.

### Power law (interpolasjon mellom NORA3-høydene)

- **Likning:** u(z) = u₁ (z/z₁)^α, α = ln(u₂/u₁) / ln(z₂/z₁)
- **Hvorfor denne:** NORA3 har vind i mange høyder (10–750 m). Power law gir en
  rett linje i log-log mellom to høyder, noe som passer en vindprofil bedre enn
  lineær interpolasjon. Vi bruker ikke en log-profil med stabilitetskorreksjon
  her, fordi det ville krevd L og z₀ og bare gjelder i overflatelaget (de nederste
  ~50–100 m), mens rotoren går opp til 270 m.
- **Kilde:** Allmennkunnskap, trenger ikke kilde.

---

## 2. Atmosfærisk stabilitet (`stability.py`)

Fremgangsmåten: NORA3-filene har ikke de turbulente flukser som trengs for å
regne ut Obukhov-lengden L direkte. Derfor beregnes bulk Richardson-tallet fra
temperaturforskjellen mellom havoverflaten og luften i 50 m, og det oversettes
til z/L med Monin-Obukhov-teori. Dette er en etablert metode når bare
middelverdier (ikke flukser) er tilgjengelig.

### Stull (1988)

- **Referanse:** Stull, R. B. (1988). *An Introduction to Boundary Layer
  Meteorology.* Kluwer Academic Publishers. (Nå Springer, doi:10.1007/978-94-009-3027-8)
- **Brukt i:** `stability.py: virtual_potential_temperature` (avsn. 1.5.1),
  `bulk_richardson` (avsn. 5.6.3)
- **Likninger i boka:**
  - Avsn. 1.5.1, s. 7, likn. (1.5.1b): θ_v = θ (1 + 0,61 r), umettet luft, r = blandingsforhold [g/g]
  - Avsn. 5.6.3, s. 177, likn. (5.6.3): R_B = g Δθ_v Δz / ( θ_v [(ΔU)² + (ΔV)²] )
- **Likninger i koden:** θ_v = T(1 + 0,61 q) + (g/c_p) z; Ri_b = (g/θ_v,0) Δθ_v z / u(z)²
- **Sammenligning med koden:**
  - Ri_b: stemmer. Mellom havoverflaten (u = 0) og høyden z er
    (ΔU)² + (ΔV)² = u(z)² og Δz = z. Koden bruker θ_v ved overflaten som referanse-θ_v.
  - θ_v: tre små tilnærminger som bør nevnes i docstringen:
    1. θ ≈ T + (g/c_p) z i stedet for θ = T (P₀/P)^0,286 (likn. 1.5.1c), altså tørradiabatisk temperaturgradient.
    2. Spesifikk fuktighet q i stedet for blandingsforhold r (q ≈ r, under 1 % forskjell).
    3. Fuktighetsleddet ganges med T i stedet for θ. Det utgjør under 0,01 K i 50 m.
  - Merk (Stull s. 177): den kritiske verdien 0,25 gjelder lokale gradienter,
    ikke tykke lag. Koden bruker ikke en kritisk verdi, bare Ri_b → z/L, så dette
    påvirker ikke oss.
- **Hvorfor denne:** θ_v tar med både fuktighet og høyde, slik at luft i ulike
  høyder kan sammenlignes på tetthet. Fuktighet betyr mye over hav. Bulk Ri
  trenger bare verdier i to nivåer, og det er det vi har. Stull sier selv at
  denne formen er den mest brukte i meteorologi fordi værmodeller gir verdier i
  diskrete høyder (s. 177).
- **Hvor:** ProQuest Ebook Central via UiB (Oria).
- **Status:** ✅ Sjekket mot boka (sidetall fra e-boka i ProQuest).
- **Kan brukes:** Ja, standard lærebok.

### Bolton (1980)

- **Referanse:** Bolton, D. (1980). The computation of equivalent potential
  temperature. *Monthly Weather Review* 108(7), 1046–1053.
  [doi:10.1175/1520-0493(1980)108<1046:TCOEPT>2.0.CO;2](https://doi.org/10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2)
- **Brukt i:** `stability.py: saturation_vapour_pressure`
- **Likning:** e_s = 6,112 exp(17,67 T / (T + 243,5)) hPa (T i °C). Koden bruker Pa (611,2).
- **Hvorfor denne:** Enkel, eksplisitt og nøyaktig (~0,1 %) i temperaturområdet
  vi har over Nordsjøen. Mye brukt i meteorologi.
- **Hvor:** Fritt tilgjengelig hos AMS (journals.ametsoc.org).
- **Status:** ✅ 🔶 Likningsnummer (10) må sjekkes.
- **Kan brukes:** Ja.

### Launiainen (1995)

- **Referanse:** Launiainen, J. (1995). Derivation of the relationship between the
  Obukhov stability parameter and the bulk Richardson number for flux-profile
  studies. *Boundary-Layer Meteorology* 76, 165–179.
  [doi:10.1007/BF00710895](https://doi.org/10.1007/BF00710895)
- **Brukt i:** `stability.py: _richardson_from_zeta`, `stability_parameter`
- **Likning:** Ri_b = ζ (ln(z/z₀) − ψ_h(ζ)) / (ln(z/z₀) − ψ_m(ζ))²
- **Hvorfor denne:** Dette er sammenhengen mellom Ri_b og z/L som følger av
  Monin-Obukhov-profilene. Den kan ikke løses analytisk for z/L, så koden lager
  en tabell og inverterer ved interpolasjon (i stedet for Launiainens
  tilnærmingsformler). Det er like nøyaktig og enklere å forstå.
- **Hvor:** Springer, via Oria / universitetsbiblioteket.
- **Status:** ✅ ⚠️ Teksten i docstringen bør presisere at vi bruker
  *sammenhengen* fra artikkelen, men løser den numerisk, ikke med Launiainens
  tilnærmingsformel. Forenklingen z₀h = z₀ er vårt valg (Launiainen tar med forholdet z₀/z₀h).
- **Kan brukes:** Ja.

### Paulson (1970) og Dyer (1974)

- **Referanser:**
  - Paulson, C. A. (1970). The mathematical representation of wind speed and
    temperature profiles in the unstable atmospheric surface layer. *J. Applied
    Meteorology* 9(6), 857–861.
    [doi:10.1175/1520-0450(1970)009<0857:TMROWS>2.0.CO;2](https://doi.org/10.1175/1520-0450(1970)009%3C0857:TMROWS%3E2.0.CO;2)
  - Dyer, A. J. (1974). A review of flux-profile relationships. *Boundary-Layer
    Meteorology* 7(3), 363–372. [doi:10.1007/BF00240838](https://doi.org/10.1007/BF00240838)
- **Brukt i:** `stability.py: psi_momentum`, `psi_heat`
- **Likninger:**
  - Ustabil (ζ < 0): x = (1 − 16ζ)^(1/4),
    ψ_m = 2 ln((1+x)/2) + ln((1+x²)/2) − 2 arctan x + π/2,
    ψ_h = 2 ln((1+x²)/2)
  - Stabil (ζ ≥ 0): ψ_m = ψ_h = −5ζ
- **Hvorfor disse:** Businger-Dyer-funksjonene er de klassiske og mest brukte
  stabilitetsfunksjonene, og Paulson ga den integrerte formen (ψ) som trengs i
  profilene. Det finnes nyere funksjoner for svært stabil luft (f.eks. Beljaars &
  Holtslag 1991), men −5ζ er standard for moderat stabil luft og holder for en
  klasseinndeling.
- **Hvor:** Paulson er fritt tilgjengelig hos AMS. Dyer via Springer / Oria.
- **Status:** ✅ 🔶 Formlene i koden stemmer med standardformene. Konstantene (16 og 5) bør sjekkes i Dyer.
- **Kan brukes:** Ja.

### Gryning et al. (2007) – stabilitetsklasser

- **Referanse:** Gryning, S.-E., Batchvarova, E., Brümmer, B., Jørgensen, H.,
  Larsen, S. (2007). On the extension of the wind profile over homogeneous terrain
  beyond the surface boundary layer. *Boundary-Layer Meteorology* 124(2), 251–268.
  [doi:10.1007/s10546-007-9166-9](https://doi.org/10.1007/s10546-007-9166-9)
- **Brukt i:** `stability.py: CLASS_NAMES`, `_INVERSE_L_EDGES`, `stability_class`
- **Hvorfor denne:** Klasseinndelingen etter L er mye brukt i vindenergi-litteraturen
  (spesielt fra DTU/Risø), og den er laget for vindprofiler opp i rotorhøyde.
- **Status:** ✅ 🔶 ⚠️ Artikkelen finnes og de bibliografiske dataene stemmer.
  Tabell 1 er ikke sjekket. Etter det vi kjenner til går de ytterste klassene i
  originalen til **−100 < L < −50** (svært ustabil) og **10 < L < 50** (svært
  stabil). At vi utvider dem til L = 0 er vårt eget valg og må sies tydelig.
  Bekreft grensene i artikkelen.
- **Kan brukes:** Ja.

### Charnock (1955)

- **Referanse:** Charnock, H. (1955). Wind stress on a water surface. *Quarterly
  Journal of the Royal Meteorological Society* 81(350), 639–640.
  [doi:10.1002/qj.49708135027](https://doi.org/10.1002/qj.49708135027)
- **Brukt i:** `stability.py`, kun i kommentaren ved `SEA_ROUGHNESS`
- **Hvorfor nevnt:** Forklarer at havets ruhet egentlig øker med vinden og bølgene
  (z₀ = α u*²/g). Vi bruker en fast z₀ i stedet, siden Ri_b → z/L er lite følsom for z₀.
- **Status:** ✅
- **Kan brukes:** Ja.

---

## 3. Turbulens (`turbulence.py`)

### IEC 61400-1:2019

- **Referanse:** IEC 61400-1:2019. *Wind energy generation systems – Part 1: Design
  requirements.* Ed. 4.0.
- **Brukt i:** `turbulence.py: SIGMA_V_RATIO`, `SIGMA_W_RATIO`, `IEC_TI_REF`, `iec_normal_turbulence`
- **Verdier/likninger:**
  - σ_v = 0,8 σ_u og σ_w = 0,5 σ_u (Kaimal-modellen, Annex C), så σ_u = √(k / 0,945)
  - I_ref = 0,16 / 0,14 / 0,12 for klasse A / B / C (Tabell 1)
  - Normalturbulensmodellen: σ₁ = I_ref (0,75 V + 5,6)
- **Hvorfor denne:** NORA3 gir bare TKE, ikke σ_u. Vi trenger et forhold mellom
  komponentene, og IEC-forholdene er de som brukes i turbindesign. NTM brukes som
  sammenligning: er turbulensen på stedet lavere enn designklassen?
- **Status:** 🔶 Formelen for NTM og I_ref-verdiene bekreftes av sekundærkilder.
  Avsnittsnummeret (6.3.2.3) og Annex C må sjekkes i 2019-utgaven. 2019-utgaven
  har også klasse **A+ (I_ref = 0,18)**, som kan legges til. Merk: i hovedteksten
  står forholdene som minimumsverdier (σ₂ ≥ 0,7 σ₁), mens 0,8 og 0,5 er fra
  Kaimal-modellen i vedlegget. Det bør gå fram av kommentaren.
- **Kan brukes:** Ja. For offshore finnes også IEC 61400-3-1:2019 med en egen
  σ₁-formel, som kan være relevant å nevne.

### IEC 61400-12-1, Annex M og Albers (2010) – turbulensnormalisering

- **Referanser:**
  - IEC 61400-12-1:2017, Annex M (informativ): normalisering av effektkurver for turbulensintensitet.
  - Albers, A. (2010). Turbulence and shear normalisation of wind turbine power
    curve. *Proc. European Wind Energy Conference (EWEC) 2010*, Warszawa,
    vol. 6, s. 4116–4123.
- **Brukt i:** `turbulence.py: turbulent_power`
- **Likning:** P_turb(U) = ∫ P(u) · N(u; U, σ_u) du (Gauss-Hermite-kvadratur)
- **Hvorfor denne:** Effektkurven er krum, så gjennomsnittseffekten over en time
  med varierende vind er ikke lik effekten ved middelvinden. Å anta normalfordelt
  vind innenfor tidssteget er prinsippet i Albers-metoden og Annex M.
- **Status:**
  - IEC Annex M: 🔶 Bekreftet at Annex M i 2017-utgaven handler om
    turbulensnormalisering og bygger på Albers-metoden.
  - Albers: ❓ Artikkelen siteres av mange (bl.a. NREL og DTU) med disse
    opplysningene, men selve artikkelen er ikke funnet. Sidetallene kommer fra siterende kilder.
  - ⚠️ Koden gjør bare *integrasjonssteget* i metoden. Annex M utleder først en
    «null-turbulens-effektkurve» fra målte data. Vi bruker i stedet den forenklede
    u³-kurven som null-turbulens-kurve. Skriv «etter prinsippet i Annex M» i
    stedet for at koden følger Annex M.
- **Kan brukes:** IEC: ja, som hovedkilde. Albers: helst ikke alene. Bruk IEC
  som hovedkilde og Albers som tillegg hvis den bekreftes.

---

## 4. Effekt og energiproduksjon (`wind_power.py`, `turbines.py`, `turbines.cfg`)

### Justus et al. (1978) – Weibull-tilpasning

- **Referanse:** Justus, C. G., Hargraves, W. R., Mikhail, A., Graber, D. (1978).
  Methods for estimating wind speed frequency distributions. *J. Applied
  Meteorology* 17(3), 350–353.
  [doi:10.1175/1520-0450(1978)017<0350:MFEWSF>2.0.CO;2](https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2)
- **Brukt i:** `wind_power.py: fit_weibull`
- **Likning:** k = (σ/ū)^(−1,086), c = ū / Γ(1 + 1/k)
- **Hvorfor denne:** Enkel og eksplisitt (ingen iterasjon), og god for 1 ≤ k ≤ 10,
  som dekker vind over hav (k ≈ 2). Alternativet er maximum likelihood
  (`scipy.stats.weibull_min.fit`), som er mer nøyaktig, men tregere og mindre gjennomsiktig.
- **Hvor:** Fritt tilgjengelig hos AMS.
- **Status:** ✅
- **Kan brukes:** Ja.

### Referanseturbinene (`turbines.cfg`)

Mangler kilde i koden i dag. Verdiene i filen stemmer med rapportene:

| Turbin | Kilde | Hvor |
|---|---|---|
| NREL 5 MW | Jonkman, J., Butterfield, S., Musial, W., Scott, G. (2009). *Definition of a 5-MW Reference Wind Turbine for Offshore System Development.* NREL/TP-500-38060. | nrel.gov (gratis) |
| DTU 10 MW | Bak, C. mfl. (2013). *The DTU 10-MW Reference Wind Turbine.* DTU Wind Energy Report-I-0092. | orbit.dtu.dk (gratis) |
| IEA 15 MW | Gaertner, E. mfl. (2020). *Definition of the IEA Wind 15-Megawatt Offshore Reference Wind Turbine.* NREL/TP-5000-75698. | nrel.gov (gratis) |

- **Status:** 🔶 ⚠️ Legg kildene inn som kommentar i `turbines.cfg`.
- **Kan brukes:** Ja. Referanseturbinene er laget nettopp for å brukes fritt i forskning.

### Forenklet effektkurve

- **Brukt i:** `turbines.py: Turbine.power`
- **Modell:** P ∝ u³ mellom cut-in og nominell vind, konstant opp til cut-out.
- **Hvorfor denne:** Den trenger bare fire tall per turbin og er lett å forstå.
  Ulempen er at den ikke viser at C_P avtar mot nominell vind. Referanserapportene
  over har ekte effektkurver som tabeller, og de kunne erstattet modellen.
- **Kilde:** Egen forenkling. Må omtales som en antagelse.

---

## 5. Tap (`wind_losses.py`)

### ISO 2533:1975 – standard lufttetthet

- **Referanse:** ISO 2533:1975. *Standard Atmosphere.*
- **Brukt i:** `wind_losses.py: STANDARD_AIR_DENSITY` (1,225 kg/m³)
- **Status:** Grei. Verdien er allmennkunnskap.

### IEC 61400-12-1 – tetthetskorreksjon

- **Brukt i:** `wind_losses.py: power_with_air_density`
- **Likning:** u_n = u (ρ/ρ₀)^(1/3) (for pitch-regulerte turbiner)
- **Hvorfor denne:** Effekten er proporsjonal med ρu³. Å skalere vinden i stedet
  for effekten gjør at nominell effekt fortsatt er taket, og det er riktig for
  pitch-regulerte turbiner. Standarden angir denne formen.
- **Status:** 🔶 Avsnittsnummeret er ikke oppgitt i koden. Se også merknaden om utgave under §1.

### Holthuijsen (2007) – bølgelengde

- **Referanse:** Holthuijsen, L. H. (2007). *Waves in Oceanic and Coastal Waters.*
  Cambridge University Press. doi:10.1017/CBO9780511618536
- **Brukt i:** `wind_losses.py: wave_tilt_amplitude`
- **Likning:** L = g T_p² / (2π) (dypt vann); maks helning = arctan(π H_s / L)
- **Hvorfor denne:** Dypvannsrelasjonen gjelder når dybden > L/2, noe som holder
  for de fleste flytende vindparker. πH/L er maks helning for en regulær bølge med høyde H.
- **Status:** 🔶 Kapittel 5 (lineær bølgeteori) må sjekkes. ⚠️ Å sette H = H_s
  for en uregelmessig sjø er vår forenkling og bør stå som det.
- **Kan brukes:** Ja.

### Egne antagelser uten kilde

Disse må enten få en kilde eller beskrives tydelig som antagelser:

| Verdi / modell | Brukt i | Merknad / mulig kilde |
|---|---|---|
| Elektrisk tap 2 % | `electrical_loss` | Typisk verdi. Mulig kilde: tapsoversikter i AEP-metodikk, f.eks. DNV eller IEA Wind. |
| 6 feil/år, 12 t reparasjon, H_s < 2 m | `weather_maintenance_loss` | Feilrater: Carroll, J., McDonald, A., McMillan, D. (2016). Failure rate, repair time and unscheduled O&M cost analysis of offshore wind turbines. *Wind Energy* 19(6), 1107–1119. [doi:10.1002/we.1887](https://doi.org/10.1002/we.1887) ✅. Grensen H_s ≈ 1,5–2 m er typisk for CTV-fartøy. |
| Fast vedlikehold 14 dager/år | `availability_loss` | Fra veileders notat. Oppgi det som kilde. |
| Restart under 20 m/s etter stormstopp | `power_with_hysteresis` | Typisk verdi, ikke fra en bestemt turbin. |
| Rotoren ser u·cos θ | `power_with_tilt` | Enkel geometri. Litteraturen bruker cos² eller cos³ på *effekten*, og vår modell tilsvarer cos³ under nominell vind. |
| Fast vinkel 5°, bølgerespons 1,0 | `wind_losses.py`, eksempelskriptet | Respons 1,0 er en øvre grense. |
| z₀ = 0,0002 m, z₀h = z₀ | `stability.py: SEA_ROUGHNESS` | Typisk verdi for åpent hav. Se Charnock. |
| 98 % relativ fuktighet over saltvann | `bulk_richardson` | Vanlig antagelse (saltvann senker metningstrykket med ~2 %). |

---

## 6. Laster (`wind_loads.py`)

### Burton et al. (2011) – aktuator-disk-teori

- **Referanse:** Burton, T., Jenkins, N., Sharpe, D., Bossanyi, E. (2011). *Wind
  Energy Handbook*, 2nd ed. Wiley. doi:10.1002/9781119992714
- **Brukt i:** `wind_loads.py: thrust_coefficient`
- **Likninger:** C_P = 4a(1−a)², C_T = 4a(1−a), Betz-grensen C_P ≤ 16/27
- **Hvorfor denne:** Vi har bare effektkurven, ikke en C_T-kurve. Aktuator-disk-teorien
  gir C_T fra C_P via induksjonsfaktoren a. Det er den enkleste fysisk konsistente
  koblingen. Den undervurderer C_T under nominell vind (står i docstringen).
- **Status:** 🔶 Avsnitt 3.2 må sjekkes.
- **Kan brukes:** Ja, standard lærebok.

### Bendat (1964) – utmatting

- **Referanse:** Bendat, J. S. (1964). *Probability functions for random responses:
  prediction of peaks, fatigue damage, and catastrophic failures.* NASA CR-33.
  [ntrs.nasa.gov/citations/19640008076](https://ntrs.nasa.gov/citations/19640008076)
- **Brukt i:** `wind_loads.py: relative_fatigue_damage`
- **Likning:** E[S^m] = (2√2 σ)^m Γ(1 + m/2) (Rayleigh-fordelte spenningsvidder, smalbånd)
- **Hvorfor denne:** Gir utmattingsskade direkte fra standardavviket, uten
  tidsserie og rainflow-telling. NORA3 har ikke data med høy nok oppløsning til rainflow.
- **Status:** ✅ Rapporten finnes på NTRS med denne tittelen og nummeret.
  Innholdsfortegnelsen dekker smalbåndstopper og utmattingsskade. 🔶 Likningen er
  ikke sjekket i teksten.
- **Kan brukes:** Ja (gratis, offentlig NASA-rapport).

### Egne antagelser uten kilde

| Verdi / modell | Brukt i | Merknad |
|---|---|---|
| Wöhler-eksponent m = 4 (stål), m = 10 (kompositt) | `WOHLER_STEEL`, `WOHLER_COMPOSITE` | Typiske verdier. Mulig kilde: DNV-RP-C203 (stål), DNV-ST-0376 (vinger). |
| σ_F = ρ A C_T U σ_u | `thrust_std` | Kvasistatisk linearisering (dF/du · σ_u). Egen utledning, vis den i docstringen. |
| (u_topp² − u_bunn²) / u_nav² | `rotor_load_asymmetry` | Egen enkel indikator, ikke en standardstørrelse. |

---

## 7. Data

- **NORA3:** Haakenstad, H., Breivik, Ø., Furevik, B. R., Reistad, M., Bohlinger,
  P., Aarnes, O. J. (2021). NORA3: A nonhydrostatic high-resolution hindcast of the
  North Sea, the Norwegian Sea, and the Barents Sea. *J. Applied Meteorology and
  Climatology* 60(10), 1443–1464.
  [doi:10.1175/JAMC-D-21-0029.1](https://doi.org/10.1175/JAMC-D-21-0029.1) ✅
- **Brukt i:** README, `tests/data/NORA3_utsira_nord_2020_2022.csv`
- **Status:** ⚠️ Mangler i README. Sjekk også MET Norways lisens og krav til
  kreditering for dataene (NORA3 er normalt CC BY 4.0) før testdataene ligger i et offentlig repo.

---

## 8. Allmennkunnskap (trenger ikke kilde)

- Power law: u(z) = u_ref (z/z_ref)^α
- Effekten i vinden: P = ½ ρ A u³, og kapasitetsfaktor
- Ideell gasslov for fuktig luft og hypsometrisk likning
- Turbulensintensitet TI = σ_u/U og TKE = ½(σ_u² + σ_v² + σ_w²)
- Matematikk: areal av striper av en sirkel, lineær interpolasjon, Gauss-Hermite-kvadratur

---

## 9. Sjekkliste

Ting som gjenstår (kryss av når det er gjort):

- [ ] Bestem utgave av IEC 61400-12-1 (2017 eller 2022) og sjekk Annex M og avsnittet om tetthetskorreksjon
- [ ] IEC 61400-1:2019: sjekk avsnitt for NTM, Tabell 1 (vurder klasse A+) og Annex C (σ-forhold)
- [x] Wagner et al. (2009): sjekk at REWS-formelen står der (likn. 6, s. 351)
- [ ] Gryning et al. (2007): sjekk klassegrensene i Tabell 1
- [ ] Albers (2010): finn artikkelen eller bruk bare IEC som kilde
- [x] Stull (1988): sjekk kapittel 1 og avsnitt 5.6
- [ ] Bolton (1980): sjekk likning (10)
- [ ] Burton et al. (2011): sjekk avsnitt 3.2
- [ ] Holthuijsen (2007): sjekk kapittel 5
- [ ] Bendat (1964): sjekk likningen for E[S^m]
- [ ] Legg turbinkildene inn i `turbines.cfg`
- [ ] Legg NORA3-referansen og krediteringen inn i README
- [ ] Rett docstringene i `turbulence.py` («etter prinsippet i Annex M») og `stability.py` (Launiainen, Gryning)

### Slik sjekkes kildene

- **Tidsskriftartikler:** Åpne DOI-lenken, eller søk på tittelen i Google Scholar / Oria.
- **AMS-artikler** (J. Applied Meteorology, Monthly Weather Review): fritt tilgjengelige på journals.ametsoc.org.
- **IEC- og ISO-standarder:** Standard Norge (standard.no). Mange universiteter har tilgang via Standard Online.
- **Lærebøker:** universitetsbiblioteket, ofte som e-bok.
- **NASA- og NREL-rapporter:** gratis på ntrs.nasa.gov og nrel.gov.
- **Veileder hos MET** har trolig tilgang til flere av bøkene og standardene.
