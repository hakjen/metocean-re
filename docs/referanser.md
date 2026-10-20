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
- **Brukt i:** `stability.py: saturation_vapour_pressure`, `specific_humidity`
- **Likning i koden:** e_s = 6,112 exp(17,67 T / (T + 243,5)) hPa (T i °C). Koden bruker Pa (611,2).
- **Hvor i artikkelen:**
  - S. 1047, underavsn. f «Saturated vapor pressure of water», høyre kolonne,
    likn. (10): e_s(T) = 6.112 exp(17.67 T / (T + 243.5)), T i °C, e_s i mb (= hPa).
    Stemmer med koden.
  - S. 1047, rett over likn. (10): tilpasset Wexler (1976) med nøyaktighet 0,1 %
    for −30 °C ≤ T ≤ 35 °C. Dekker temperaturene over Nordsjøen.
  - S. 1047, venstre kolonne, «d. Water vapor»: ε = R_d/R_v = 0,6220. Dette er
    konstanten 0,622 (og 0,378 = 1 − 0,622) i `specific_humidity`.
- **Hvorfor denne:** Enkel, eksplisitt og nøyaktig i temperaturområdet vi har.
  Den eldre Tetens-formelen, likn. (8) på samme side, har 2 % feil ved −30 °C.
  Bolton laget likn. (10) som en forbedring, og den er standardvalget i meteorologi.
- **Hvor:** Fritt tilgjengelig hos AMS (journals.ametsoc.org).
- **Status:** ✅ Sjekket mot artikkelen.
- **Kan brukes:** Ja.

### Fairall mfl. (2003) – damptrykk over saltvann

- **Referanse:** Fairall, C. W., Bradley, E. F., Hare, J. E., Grachev, A. A.,
  Edson, J. B. (2003). Bulk parameterization of air–sea fluxes: Updates and
  verification for the COARE algorithm. *J. Climate* 16(4), 571–591.
  [doi:10.1175/1520-0442(2003)016<0571:BPOASF>2.0.CO;2](https://doi.org/10.1175/1520-0442(2003)016%3C0571:BPOASF%3E2.0.CO;2)
- **Brukt i:** `stability.py: bulk_richardson` (`specific_humidity(sst, 0.98, p_0)`)
- **Hvor i artikkelen** (PDF-side n = s. 570 + n):
  - Avsn. 2b «COARE 2.5», s. 573: fuktigheten ved overflaten beregnes fra
    overflatetemperaturen og «the vapor pressure of seawater (0.98 times the vapor
    pressure of pure water; Kraus and Businger 1994)».
  - S. 584: «reduction in seawater vapor pressure by 2% due to salinity».
- **Sammenligning med koden:** Stemmer. Koden ganger metningstrykket ved
  havoverflatens temperatur med 0,98. Docstringen kalte det tidligere «98 %
  relative humidity», og er nå presisert til at det er saltholdigheten som senker
  damptrykket.
- **Begrensning:** COARE bruker temperaturen helt i overflaten («cool skin»), som
  er noen tideler av en grad kaldere enn vannet under. Vi bruker havoverflate-
  temperaturen fra NORA3. Liten betydning for oss.
- **Hvorfor denne:** COARE er en av de mest brukte algoritmene for fluks mellom
  hav og atmosfære, så den er en god kilde for faktoren. Opprinnelig kilde er
  læreboka Kraus og Businger (1994).
- **Status:** ✅ Sjekket mot artikkelen.
- **Kan brukes:** Ja.

### Launiainen (1995)

- **Referanse:** Launiainen, J. (1995). Derivation of the relationship between the
  Obukhov stability parameter and the bulk Richardson number for flux-profile
  studies. *Boundary-Layer Meteorology* 76, 165–179.
  [doi:10.1007/BF00710895](https://doi.org/10.1007/BF00710895)
- **Brukt i:** `stability.py: _richardson_from_zeta`, `stability_parameter`
- **Likning i koden:** Ri_b = ζ (ln(z/z₀) − ψ_h(ζ)) / (ln(z/z₀) − ψ_m(ζ))²
- **Hvor i artikkelen:**
  - Avsn. 2.1, s. 167, likn. (2): ζ = R_z (ln z/z₀ − ψ_M)² / ( α_HN (ln z/z_T − ψ_H) ).
    Koden har samme likning, løst for Ri_b, med α_HN = 1 og z_T = z₀.
  - S. 167, under likn. (2): α_HN ≈ 1 er brukt i artikkelen.
  - S. 167, etter likn. (2): metoden koden bruker, å lage sammenhengen for
    vilkårlige ζ og finne ζ ved «inverse mapping» fra observert R_z.
  - Avsn. 2.2, s. 167: z_T ≈ z₀ (C_D ≈ C_H) er «generally true over water in
    light to moderate winds». Dette støtter forenklingen vår.
  - Vedlegget, s. 177–178: (A8) stabil ψ = −bζ med b ≈ 5,2 (Webb 1970), koden
    bruker 5 (Dyer). (A10)–(A11) ustabil Businger-Dyer med konstant 15–16,
    koden bruker 16.
- **Hvorfor denne:** Dette er sammenhengen mellom Ri_b og z/L som følger av
  Monin-Obukhov-profilene. Den kan ikke løses analytisk for z/L. Koden
  inverterer den ved interpolasjon i en tabell, slik artikkelen beskriver, i
  stedet for å bruke Launiainens tilnærmingsformler (4)–(11). Det er like
  nøyaktig og enklere å forstå.
- **Begrensning:** Avsn. 2.3, s. 169: den lineære formen ψ = −5ζ gir for sterke
  stabilitetseffekter når ζ > 0,5. Launiainen anbefaler Holtslag og De Bruin
  (1988) for sterk stabilitet. Koden bruker −5ζ opp til ζ = 10, så L-verdiene i
  klassen «very stable» er usikre.
- **Hvor:** Springer, via Oria / universitetsbiblioteket.
- **Status:** ✅ Sjekket mot artikkelen.
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
- **Hvor i Paulson** (formlene har ikke likningsnummer, så sidetall brukes):
  - S. 858, avsn. 2 «Profile representations», høyre kolonne: de integrerte
    B-D-formene ψ₁ = 2 ln[(1+x)/2] + ln[(1+x²)/2] − 2 tan⁻¹x + π/2 og
    ψ₂ = 2 ln[(1+x²)/2], med x = (1 − γ z/L)^(1/4). Begge stemmer nøyaktig
    med `psi_momentum` og `psi_heat` for ustabil luft.
  - S. 858: utgangspunktet φ₁ = (1 − γ z/L)^(−1/4), φ₂ = (1 − γ z/L)^(−1/2), og
    definisjonen av ψ i likn. (3).
  - S. 859, avsn. 4: «The B-D representation gives the best fit to both the
    wind and temperature profiles for γ = 16». Dette støtter konstanten 16 i koden.
  - S. 860, konklusjonen: B-D gir best samtidig tilpasning for vind og
    temperatur. Log-lineær form passer bare nær nøytral luft.
- **Begrensning:** Paulsons test (s. 859) bygger på 34 profiler fra Kerang,
  Australia: tørt land, 0,5–16 m, bare ustabil luft. Vi bruker formene i 50 m
  over hav, som er vanlig praksis, men en ekstrapolering.
- **Hvorfor disse:** Businger-Dyer-funksjonene er de klassiske og mest brukte
  stabilitetsfunksjonene, og Paulson ga den integrerte formen (ψ) som trengs i
  profilene. Det finnes nyere funksjoner for svært stabil luft (f.eks. Beljaars &
  Holtslag 1991), men −5ζ er standard for moderat stabil luft og holder for en
  klasseinndeling.
- **Hvor:** Paulson via JSTOR / AMS (UiB). Dyer via Springer / Oria.
- **Status:**
  - Paulson: ✅ Sjekket mot artikkelen. Hos Paulson tilskrives B-D Businger
    (1966) og Dyer (upublisert); Dyer (1974) er oversiktsartikkelen som
    oppsummerte formene senere.
  - Dyer: ✅ Sjekket mot artikkelen (ingen likningsnumre, så sidetall brukes):
    - Sammendraget (s. 363) og avsn. 4 «Concluding Remarks» (s. 371): anbefalte
      former. Ustabil: φ_M = (1 − 16 z/L)^(−1/4), φ_H = (1 − 16 z/L)^(−1/2).
      Stabil: φ_M = φ_H = 1 + 5 z/L. Konstantene 16 og 5 stemmer med koden.
    - Dyer gir gradientformene φ, ikke ψ. ψ = −5 z/L for stabil luft er
      utledet ved å integrere φ = 1 + 5 z/L (definisjonen av ψ i Paulsons likn. (3)).
    - S. 371: formene er fra Dyer og Hicks (1970), Quart. J. Roy. Meteor. Soc.
      96, 715–721, som er originalkilden om den skulle trengs.
    - S. 371: «on the stable side, the experimental material is rather
      limited». Dette passer med Launiainens advarsel om −5ζ ved sterk stabilitet.
- **Kan brukes:** Ja.

### Gryning et al. (2007) – stabilitetsklasser

- **Referanse:** Gryning, S.-E., Batchvarova, E., Brümmer, B., Jørgensen, H.,
  Larsen, S. (2007). On the extension of the wind profile over homogeneous terrain
  beyond the surface boundary layer. *Boundary-Layer Meteorology* 124(2), 251–268.
  [doi:10.1007/s10546-007-9166-9](https://doi.org/10.1007/s10546-007-9166-9)
- **Brukt i:** `stability.py: CLASS_NAMES`, `_INVERSE_L_EDGES`, `stability_class`
- **Hvorfor denne:** Klasseinndelingen etter L er mye brukt i vindenergi-litteraturen
  (spesielt fra DTU/Risø), og den er laget for vindprofiler opp i rotorhøyde.
- **Hvor i artikkelen:**
  - Tabell 1, s. 260, teksten under tabellen: «10<L<50 (very stable);
    50<L<200 (Stable); 200<L<500 (near neutral/stable); L>500 or L<−500
    (neutral); −500<L<−200 (near neutral/unstable); −200<L<−100 (unstable)
    and −100<L<−50 (very unstable)».
  - Avsn. 3.1 «Data processing», s. 259: målingene er delt i «seven stability
    classes according to the Obukhov length». Bare vind over 3 m/s i 10 m er brukt.
- **Sammenligning med koden:** De fem midterste klassene stemmer. De to ytterste
  er utvidet i koden: very unstable −100 < L < 0 (Gryning: −100 < L < −50) og
  very stable 0 < L < 50 (Gryning: 10 < L < 50). Om grensene er med (≤) eller
  ikke (<), har ingen praktisk betydning.
- **Hvorfor vi utvider til L = 0:**
  - Alle tidssteg må få en klasse. Ellers faller de mest ekstreme tilfellene ut
    av `losses_by_stability`, og andelene summerer ikke til 100 %.
  - Jo nærmere L er 0, jo sterkere er stabiliteten eller ustabiliteten, så disse
    tidsstegene hører naturlig hjemme i de ytterste klassene.
  - Gryning trengte pålitelige middelprofiler per klasse og utelot svak vind og
    svært liten |L|, der Monin-Obukhov-teorien er upålitelig. Vi trenger bare å
    sortere tidssteg.
  - Ulempe: L er minst sikker nettopp her (−5ζ er for sterk ved sterk stabilitet,
    se Launiainen og Dyer). Med z/L begrenset til [−100, 10] i 50 m blir L aldri
    mindre enn 5 m på stabil side eller nærmere 0 enn −0,5 m på ustabil side.
- **Begrensning:** Datagrunnlaget er fra land (Høvsøre, sektoren fra land, og
  Hamburg), med L målt i 10–12 m (Tabell 1). Vi beregner L fra Ri_b i 50 m over
  hav. Klasseinndelingen brukes mye offshore også.
- **Status:** ✅ Sjekket mot artikkelen.
- **Kan brukes:** Ja.

### Charnock (1955)

- **Referanse:** Charnock, H. (1955). Wind stress on a water surface. *Quarterly
  Journal of the Royal Meteorological Society* 81(350), 639–640.
  [doi:10.1002/qj.49708135027](https://doi.org/10.1002/qj.49708135027)
- **Brukt i:** `stability.py`, kun i kommentaren ved `SEA_ROUGHNESS`
- **Hvor i artikkelen:** S. 639, sammendraget: z(0) «was largely determined by
  u*», og «g z(0)/u*² = constant». Dette er Charnock-relasjonen z₀ = α u*²/g.
- **Hvorfor nevnt:** Forklarer at havets ruhet egentlig øker med friksjonshastigheten
  u*, altså med vinden. Den fysiske tolkningen er at sterkere vind gir ruere
  overflate (bølger), men det skriver ikke Charnock selv. Vi bruker en fast z₀ i
  stedet, siden ln(z/z₀) og dermed Ri_b → z/L endrer seg relativt lite med z₀.
- **Rimelighetssjekk:** Med α ≈ 0,011 (vanlig verdi i senere litteratur, ikke fra
  denne artikkelen) og u* ≈ 0,4 m/s (moderat vind) blir z₀ ≈ 0,0002 m, som er
  verdien koden bruker.
- **Begrensning:** Charnocks målinger er fra et reservoar (1,6 × 1 km), i de
  nederste 8 m, ikke fra åpent hav. Relasjonen er likevel blitt standard for hav.
- **Status:** ✅ Sjekket mot artikkelen. Kommentaren i koden er presisert fra
  «grows with the waves» til «grows with the friction velocity».
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

### Albers (2010) og IEC 61400-12-1, Annex M – turbulensnormalisering

- **Referanser:**
  - Albers, A. (2010). Turbulence and shear normalisation of wind turbine power
    curve. *Proc. European Wind Energy Conference (EWEC) 2010*, Warszawa,
    vol. 6, s. 4116–4123. Deutsche WindGuard Consulting GmbH.
  - Se også: IEC 61400-12-1:2017, Annex M (informativt vedlegg): normalisering
    av effektkurver for turbulensintensitet. Bygger på Albers-metoden.
- **Brukt i:** `turbulence.py: turbulent_power`
- **Likning i koden:** P_turb(U) = ∫ P(u) · N(u; U, σ_u) du (Gauss-Hermite-kvadratur)
- **Hvor i Albers** (PDF uten trykte sidetall, så PDF-sider brukes):
  - Avsn. 3.1, likn. (1), PDF-s. 2: P_sim(v) = ∫ P_I=0(v) f(v) dv, der f(v)
    tilnærmes med en normalfordeling bestemt av middelvind og turbulensintensitet
    («Normal Distribution Model»). Stemmer med koden.
  - Avsn. 3.1, PDF-s. 2: hovedantagelsen at turbinen hele tiden følger samme
    effektkurve («zero turbulence power curve»), fordi den reagerer i løpet av
    sekunder mens vindvariasjonene skjer over ~100 s.
  - Avsn. 3.2 og figur 1, PDF-s. 2–3: null-turbulens-kurven lages i tre steg fra
    målte data. Første steg er P ∝ v³ fra cut-in til nominell effekt.
  - Avsn. 5.1, PDF-s. 4–5: metoden kan brukes til å tilpasse teoretiske
    effektkurver til turbulensen på et sted, for vindressursberegninger. Slik bruker vi den.
  - Avsn. 7, PDF-s. 6: metoden «shifts power curve raw data always in the right
    direction», men effekten blir ofte undervurdert når turbulensen avviker mye
    fra referansen.
- **Sammenligning med koden:**
  - Integrasjonen (likn. 1) stemmer.
  - ⚠️ Vi bruker den forenklede u³-kurven direkte som null-turbulens-kurve, uten
    Albers' justering mot målte data (avsn. 3.2). Kurven vår ligner Albers' første
    steg (P ∝ v³), så dette er en rimelig forenkling, men den må stå som det.
  - Albers korrigerer for variasjon innenfor 10-minutters perioder. Vi bruker
    σ_u fra NORA3-TKE (modellverdier per time eller tredje time). Prinsippet er
    det samme, men tidsskalaen er en annen.
- **Hvorfor denne:** Effektkurven er krum, så gjennomsnittseffekten over et
  tidssteg med varierende vind er ikke lik effekten ved middelvinden. Albers'
  metode er enkel, fungerer for alle turbintyper og er tatt inn i IEC 61400-12-1.
- **Status:**
  - Albers: ✅ Sjekket mot artikkelen. Albers henviser selv til IEC 61400-12-1:2005,
    og metoden ble foreslått for neste utgave av standarden, som ble Annex M i 2017-utgaven.
    Sidetallene i proceedings (4116–4123) kommer fra siterende kilder.
  - IEC Annex M: 🔶 Ikke lest. Bekreftet via sekundærkilder at vedlegget handler
    om turbulensnormalisering og bygger på Albers.
- **Kan brukes:** Ja. Albers er originalkilden for metoden og brukes som
  hovedkilde. IEC Annex M som «se også».

---

## 4. Effekt og energiproduksjon (`wind_power.py`, `turbines.py`, `turbines.cfg`)

### Justus et al. (1978) – Weibull-tilpasning

- **Referanse:** Justus, C. G., Hargraves, W. R., Mikhail, A., Graber, D. (1978).
  Methods for estimating wind speed frequency distributions. *J. Applied
  Meteorology* 17(3), 350–353.
  [doi:10.1175/1520-0450(1978)017<0350:MFEWSF>2.0.CO;2](https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2)
- **Brukt i:** `wind_power.py: fit_weibull`, `weibull_pdf`
- **Likning i koden:** k = (σ/ū)^(−1,086), c = ū / Γ(1 + 1/k)
- **Hvor i artikkelen:**
  - Avsn. 2c «Mean wind speed and standard deviation – Method 3», s. 351, høyre
    kolonne: likn. (13) V̄ = c Γ(1 + 1/k), likn. (14) den eksakte sammenhengen
    mellom σ/V̄ og k, **likn. (15) k = (σ/V̄)^(−1.086)** som tilnærming til (14), og
    **likn. (16) c = V̄/Γ(1 + 1/k)**. Stemmer med koden.
  - S. 351: σ² = ⟨(V − V̄)²⟩, altså populasjonsstandardavviket, som er det
    `numpy.std()` gir som standard.
  - S. 350, likn. (1): Weibull-fordelingen. Stemmer med `weibull_pdf`.
  - S. 352, høyre kolonne: maximum likelihood (Takle og Brown 1977) er
    «potentially more accurate but somewhat more difficult to apply».
- **Hvorfor denne:** Enkel og eksplisitt (ingen iterasjon) og trenger bare
  middelverdi og standardavvik. Alternativet er maximum likelihood
  (`scipy.stats.weibull_min.fit`), som kan være mer nøyaktig, men er tregere og mindre gjennomsiktig.
- **Merk:** Tabell 2 (s. 352) tester metodene 1, 4 og 5, ikke metode 3, så
  artikkelen gir ikke et mål på nøyaktigheten til likn. (15).
- **Hvor:** Fritt tilgjengelig hos AMS / JSTOR.
- **Status:** ✅ Sjekket mot artikkelen.
- **Kan brukes:** Ja.

### Referanseturbinene (`turbines.cfg`)

Referanseturbiner er offentlige turbindesign laget av forskningsinstitutter, slik
at forskere kan regne på samme turbin og sammenligne resultater. Vi bruker seks
tall per turbin: nominell effekt, cut-in, nominell vind, cut-out, navhøyde og rotordiameter.

| Turbin | Kilde | Tabell | Hvor |
|---|---|---|---|
| NREL 5 MW | Jonkman, J., Butterfield, S., Musial, W., Scott, G. (2009). *Definition of a 5-MW Reference Wind Turbine for Offshore System Development.* NREL/TP-500-38060. | Tabell 1-1 «Gross Properties», s. 2 | nrel.gov (gratis) |
| DTU 10 MW | Bak, C., Zahle, F., Bitsche, R., Kim, T., Yde, A., Henriksen, L. C., Natarajan, A., Hansen, M. H. (2013). *Description of the DTU 10 MW Reference Wind Turbine.* DTU Wind Energy Report-I-0092. | Tabell 2.1 «Key parameters», s. 13, kolonnen «DTU 10MW RWT» | orbit.dtu.dk (gratis) |
| IEA 15 MW | Gaertner, E. mfl. (2020). *Definition of the IEA Wind 15-Megawatt Offshore Reference Wind Turbine.* NREL/TP-5000-75698. | Tabell 1-1 «Key Parameters», s. 5 | nrel.gov (gratis) |

- **Sammenligning med koden:** Alle seks tallene i `turbines.cfg` stemmer for alle
  tre turbinene. IEA-rapportens tabell viser også DTU 10 MW, med de samme tallene.
- **Merk:** NREL-rapporten (s. 3) sier at diameteren på 126 m ser bort fra precone
  (2,5°), så den faktiske diameteren er litt mindre (under 0,1 %). Kan ignoreres.
- **Status:** ✅ Sjekket mot rapportene. Kildene står nå som kommentarer i `turbines.cfg`.
- **Kan brukes:** Ja. Referanseturbinene er laget nettopp for å brukes fritt i forskning.

### Forenklet effektkurve

- **Brukt i:** `turbines.py: Turbine.power`
- **Modell:** P ∝ u³ mellom cut-in og nominell vind, konstant opp til cut-out.
- **Hvorfor denne:** Den trenger bare fire tall per turbin og er lett å forstå.
  Ulempen er at den ikke viser at C_P avtar mot nominell vind. Referanserapportene
  over har ekte effektkurver som tabeller, og de kunne erstattet modellen.
- **Kilde:** Egen forenkling. Må omtales som en antagelse. Albers (2010), figur 1,
  bruker samme form (P ∝ v³ fra cut-in til nominell effekt) som første steg for en
  null-turbulens-effektkurve, så formen har noe støtte.

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
- **Likning i koden:** L = g T_p² / (2π) (dypt vann); maks helning = arctan(π H_s / L)
- **Hvor i boka** (kap. 5 «Linear wave theory (oceanic waters)», s. 105–143):
  - Avsn. 5.4.3 «Dynamics», s. 123, likn. (5.4.18): L₀ = g T²/(2π) (dypt vann).
    Stemmer med koden. Rett over står den generelle formen for alle dyp, likn. (5.4.17):
    L = g T²/(2π) · tanh(2πd/L).
  - Note 5A, s. 118: harmonisk bølge η = (H/2) sin(2πt/T − 2πx/L). Største helning
    (H/2)(2π/L) = πH/L følger direkte av dette (står ikke ferdig utregnet i boka).
  - S. 118: lineær teori forutsetter liten amplitude (ak ≪ 2π). Avsn. 5.1, s. 105:
    teorien bør ikke brukes for bratte bølger.
- **Hvorfor denne:** Dypvannsrelasjonen er eksplisitt og gjelder når dybden er mer
  enn omtrent halve bølgelengden. Med Tp = 15 s gir likn. (5.4.18) L₀ ≈ 350 m, så
  dybden bør være over ca. 175 m. Havdybden på Utsira Nord er 250–280 m
  (Equinor, equinor.com/no/energi/utsira-nord). Med d = 250 m holder
  dypvannsformen (d > L/2) for Tp under ca. 18 s, altså praktisk talt alle bølger.
- **Begrensning:** ⚠️ Boka beskriver en regulær bølge med høyde H. At vi setter
  H = H_s for en uregelmessig sjø, er vår forenkling og står ikke i boka.
- **Hvor:** Cambridge Core via UiB (kapittel 5 som PDF).
- **Status:** ✅ Sjekket mot boka.
- **Kan brukes:** Ja.

### Carroll mfl. (2016) – feilrate og reparasjonstid

- **Referanse:** Carroll, J., McDonald, A., McMillan, D. (2016). Failure rate,
  repair time and unscheduled O&M cost analysis of offshore wind turbines.
  *Wind Energy* 19(6), 1107–1119.
  [doi:10.1002/we.1887](https://doi.org/10.1002/we.1887)
- **Brukt i:** `wind_losses.py: weather_maintenance_loss`, `annual_energy_losses`;
  `plots/wind_losses.py: plot_maintenance_downtime` (standardverdiene)
- **Verdier i koden:** 8,3 feil per turbin per år, 12 t reparasjonstid
- **Hvor i artikkelen** (PDF-side n = s. 1106 + n):
  - Avsn. 5.1, s. 1110: «The average failure rate for an offshore wind turbine
    from this analysis is 8.3 failures per turbine per year», fordelt på 6,2 små
    reparasjoner, 1,1 store reparasjoner og 0,3 store utskiftinger.
  - Konklusjonen, s. 1117: feilraten flater ut på ca. 10 per turbin per år fra
    tredje driftsår.
  - Tabell II, s. 1117: feilrate og reparasjonstid per kategori: små 6,81/år og
    6,67 t, store 1,17/år og 17,64 t, utskifting 0,29/år og 116,19 t. Tabellen sier
    «days», men tallene må være timer (referansekolonnen har samme verdier som
    Tabell I, der enheten er timer).
  - Avsn. 5.5, s. 1115: reparasjonstiden er bare tiden teknikerne er i turbinen,
    uten reisetid og venting på tilgang.
- **Sammenligning med koden:**
  - Feilraten er endret fra 6 til 8,3 (avtalt med Håkon) for å stemme med kilden.
  - 12 t er Carrolls reparasjonstid vektet med feilrate:
    (6,81·6,67 + 1,17·17,64 + 0,29·116,19) / 8,27 ≈ 12,1 t.
- **Begrensninger:** Carroll teller som feil ethvert ikke-planlagt besøk der det
  brukes materiell (s. 1117), også små feil. Koden lar alle feil stoppe turbinen
  til et værvindu er funnet, og bruker samme Hs-grense for alle, selv om store
  utskiftinger krever andre fartøy (Tabell I). Hs-grensen står ikke i Carroll.
- **Status:** ✅ Sjekket mot artikkelen.
- **Kan brukes:** Ja.

### Egne antagelser uten kilde

Verdiene er delt i tre: **løst** (har fått kilde eller støtte), **trenger kilde**
(påvirker resultatene og ser ut som fakta) og **egen antagelse** (bevisste valg,
avtalt med veileder eller enkel matematikk, som bare må stå tydelig som antagelser).

| Verdi / modell | Brukt i | Status | Merknad / mulig kilde |
|---|---|---|---|
| z₀ = 0,0002 m | `stability.py: SEA_ROUGHNESS` | ✅ Løst | Tilsvarer Charnock-relasjonen ved moderat vind (se Charnock). |
| z₀h = z₀ | `stability.py: _richardson_from_zeta` | ✅ Løst | Launiainen (1995), avsn. 2.2: gjelder over hav i svak til moderat vind. |
| 8,3 feil/år, 12 t reparasjon | `weather_maintenance_loss`, `annual_energy_losses`, `plot_maintenance_downtime` | ✅ Løst | Carroll mfl. (2016), se egen oppføring under. Feilraten er endret fra 6 til 8,3 etter avtale med Håkon, slik at den stemmer med kilden. 12 t er uendret og stemmer med Carrolls vektede gjennomsnitt (≈ 12,1 t). |
| H_s < 2 m for tilgang | `weather_maintenance_loss` | 🔶 Trenger kilde | Resultatet er svært følsomt for denne verdien. Grensen for vanlige servicefartøy (CTV) er ofte 1,5–2 m. Står ikke i Carroll (Tabell I nevner bare at CTV brukes). Trenger en annen kilde, f.eks. DNV. |
| Faktor 0,98 for damptrykk over saltvann | `bulk_richardson` | ✅ Løst | Fairall mfl. (2003), se egen oppføring under avsn. 2. |
| Elektrisk tap 2 % | `electrical_loss` | Egen antagelse | Typisk verdi (1–3 %). En kilde ville styrket den. NB: generatorvirkningsgraden (94,4 % i NREL 5 MW-rapporten) er ikke det samme. Den er allerede med i effektkurven. |
| Fast vedlikehold 14 dager/år | `availability_loss` | Egen antagelse | Avtalt med veileder («ca. 2 uker minus i året»). Oppgis som «etter avtale med veileder (MET)». |
| Restart under 20 m/s etter stormstopp | `power_with_hysteresis` | Egen antagelse | Typisk verdi til illustrasjon, ikke fra en bestemt turbin. |
| Rotoren ser u·cos θ | `power_with_tilt` | Egen antagelse | Enkel geometri. Litteraturen bruker cos² eller cos³ på *effekten*, og vår modell tilsvarer cos³ under nominell vind. |
| Fast vinkel 5°, bølgerespons 1,0 | `wind_losses.py`, eksempelskriptet | Egen antagelse | Scenariovalg. Respons 1,0 er en bevisst øvre grense. |

---

## 6. Laster (`wind_loads.py`)

### Burton et al. (2021) – aktuator-disk-teori

- **Referanse:** Burton, T., Jenkins, N., Bossanyi, E., Sharpe, D., Graham, M.
  (2021). *Wind Energy Handbook*, 3rd ed. Wiley.
  [doi:10.1002/9781119451143](https://doi.org/10.1002/9781119451143)
  (Koden henviste tidligere til 2. utgave, 2011. Byttet til 3. utgave, som er den
  som er sjekket. Avsnittsnummeret er det samme.)
- **Brukt i:** `wind_loads.py: thrust_coefficient`
- **Likninger i koden:** C_P = 4a(1−a)², C_T = 4a(1−a), Betz-grensen C_P ≤ 16/27,
  a funnet fra C_P på 0 ≤ a ≤ 1/3
- **Hvor i boka** (kap. 3 «Aerodynamics of horizontal axis wind turbines»):
  - Avsn. 3.2 «The actuator disc concept», s. 41–42, likn. (3.2): U_D = U∞(1 − a)
  - Avsn. 3.2.2, s. 43, likn. (3.12): C_P = 4a(1 − a)²
  - Avsn. 3.2.3, s. 43, likn. (3.13): maks ved a = 1/3, C_P,max = 16/27 ≈ 0,593 (Betz-grensen)
  - Avsn. 3.2.4, s. 44, likn. (3.16): C_T = 4a(1 − a)
  - S. 44, under likn. (3.16): momentumteorien gjelder ikke for a ≥ 1/2. Koden
    bruker bare a ≤ 1/3 og er godt innenfor.
- **Hvorfor denne:** Vi har bare effektkurven, ikke en C_T-kurve. Aktuator-disk-teorien
  gir C_T fra C_P via induksjonsfaktoren a. Det er den enkleste fysisk konsistente
  koblingen. Den undervurderer C_T under nominell vind fordi ideell teori ikke tar
  med tap (står i docstringen).
- **Hvor:** Wiley Online Library via UiB (kapittel 3 som PDF).
- **Status:** ✅ Sjekket mot boka (3. utgave).
- **Kan brukes:** Ja, standard lærebok.

### Bendat (1964) – utmatting

- **Referanse:** Bendat, J. S. (1964). *Probability functions for random responses:
  prediction of peaks, fatigue damage, and catastrophic failures.* NASA CR-33.
  [ntrs.nasa.gov/citations/19640008076](https://ntrs.nasa.gov/citations/19640008076)
- **Brukt i:** `wind_loads.py: relative_fatigue_damage`
- **Likning i koden:** E[S^m] = (2√2 σ)^m Γ(1 + m/2) (Rayleigh-fordelte spenningsvidder, smalbånd)
- **Hvor i rapporten** (rapportens sidetall = PDF-sidetall − 3):
  - Avsn. 3 «Peak Probability Functions for Narrow Band Noise», likn. (27)–(28),
    rapport-s. 12 (PDF-s. 15): toppene i smalbåndet normalfordelt støy er Rayleigh-fordelte.
  - Avsn. 6 «Expected Fatigue Damage and its Variance», likn. (43)–(45),
    rapport-s. 19–20 (PDF-s. 22–23): Palmgren-Miner, skade per halvsyklus d = K |S|^b.
  - Avsn. 7.1 «Expected Value in Damage Estimates», likn. (80)–(82),
    rapport-s. 29–30 (PDF-s. 32–33): forventet skade ∝ (√2 σ)^b Γ(1 + b/2).
- **Sammenligning med koden:** Bendat regner med toppamplituder, (√2 σ)^b. Koden
  regner med spenningsvidder (dobbelt så store), (2√2 σ)^m. Forskjellen er
  konstanten 2^m, som forsvinner fordi koden bare bruker hvert tidsstegs andel av
  total skade. Resultatet er det samme.
- **Forenklinger:**
  - Samme antall sykluser i hvert tidssteg. Hos Bendat er antallet halvsykluser
    m = 2N₀⁺T (likn. 48) og avhenger av hvor ofte signalet krysser null.
  - Spenningen antas proporsjonal med skyvekraften, så σ = standardavviket til skyvekraften.
  - Smalbånd (avsn. 7.1). Ekte turbinlaster er ofte mer bredbåndet.
- **Hvorfor denne:** Gir utmattingsskade direkte fra standardavviket, uten
  tidsserie og rainflow-telling. NORA3 har ikke data med høy nok oppløsning til rainflow.
- **Status:** ✅ Sjekket mot rapporten.
- **Kan brukes:** Ja (gratis, offentlig NASA-rapport).

### Egne antagelser uten kilde

| Verdi / modell | Brukt i | Status | Merknad |
|---|---|---|---|
| Wöhler-eksponent m = 10 (kompositt, blader) | `WOHLER_COMPOSITE` | ✅ Løst | DTU 10 MW-rapporten (Bak mfl. 2013), avsn. 6.4.4, s. 74: «For the blade loads a Wöhler exponent of m = 10 has been used.» |
| Wöhler-eksponent m = 4 (stål, tårn) | `WOHLER_STEEL` | ⚠️ Avvik | Samme sted i DTU-rapporten: «Other components are assumed to be steel, m = 3.» DNV-RP-C203 bruker også m = 3 (og m = 5 ved mange sykluser) for sveiset stål. m = 4 er vanlig i vindlast-studier, men har ingen kilde ennå. **Valg:** bytte til m = 3 med DTU som kilde, eller beholde m = 4 og finne en kilde. Avklares med veileder. |
| σ_F = ρ A C_T U σ_u | `thrust_std` | Egen antagelse | Kvasistatisk linearisering (dF/du · σ_u). Matematisk utledning, vis den i docstringen. |
| (u_topp² − u_bunn²) / u_nav² | `rotor_load_asymmetry` | Egen antagelse | Egen enkel indikator, ikke en standardstørrelse. |

---

## 7. Data

- **NORA3:** Haakenstad, H., Breivik, Ø., Furevik, B. R., Reistad, M., Bohlinger,
  P., Aarnes, O. J. (2021). NORA3: A nonhydrostatic high-resolution hindcast of the
  North Sea, the Norwegian Sea, and the Barents Sea. *J. Applied Meteorology and
  Climatology* 60(10), 1443–1464.
  [doi:10.1175/JAMC-D-21-0029.1](https://doi.org/10.1175/JAMC-D-21-0029.1) ✅
- **Brukt i:** README, `tests/data/NORA3_utsira_nord_2020_2022.csv`
- **Lisens:** MET Norways datakatalog oppgir CC BY 4.0 for NORA3
  ([data.met.no](https://data.met.no/dataset/ddb4c5d1-70b5-4d09-98a8-fadbf5e2d2ba)).
  CC BY krever at kilden krediteres, og det er gjort i README. Lisensen kan variere
  mellom NORA3-produktene, så sjekk lisensfeltet for hvert produkt som brukes
  (vind, bølger, atmosfære).
- **Status:** ✅ Referansen og krediteringen står i README.
- **Gjenstår:** Haakenstad mfl. (2021) dekker atmosfæredelen. Bølgedataene (Hs, Tp)
  kommer fra NORA3-bølgehindcasten, som har en egen referanse. Den er ikke funnet ennå.

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
- [x] Launiainen (1995): sjekk likn. (2) og metoden (s. 167)
- [x] Paulson (1970): sjekk ψ_m, ψ_h og γ = 16 (s. 858–859)
- [x] Dyer (1974): sjekk −5ζ (stabil) og 16 (ustabil)
- [x] Gryning et al. (2007): sjekk klassegrensene i Tabell 1
- [x] Albers (2010): artikkelen funnet og likn. (1) sjekket
- [x] Stull (1988): sjekk kapittel 1 og avsnitt 5.6
- [x] Bolton (1980): sjekk likning (10) (s. 1047)
- [x] Burton et al. (2021, 3. utg.): sjekk avsnitt 3.2 (likn. 3.12, 3.13, 3.16)
- [x] Holthuijsen (2007): sjekk kapittel 5 (likn. 5.4.18, s. 123)
- [x] Bendat (1964): sjekk likningen for E[S^m] (likn. 80–82)
- [x] Justus et al. (1978): sjekk likn. (15)–(16) (s. 351)
- [x] Charnock (1955): sjekk relasjonen z₀ = α u*²/g (s. 639)
- [x] Legg turbinkildene inn i `turbines.cfg` (tallene sjekket mot rapportene)
- [x] Legg NORA3-referansen og krediteringen inn i README
- [ ] NORA3-bølgedataene (Hs, Tp): finn og legg inn referansen for bølgedelen av NORA3
- [x] Rett docstringene i `turbulence.py` (Albers, Annex M) og `stability.py` (Launiainen, Gryning)
- [x] Fairall et al. (2003): sjekk faktoren 0,98 (s. 573)
- [x] Carroll et al. (2016): sjekk feilrate og reparasjonstid (s. 1110, 1117); feilraten endret til 8,3
- [x] Wöhler-eksponent for blader, m = 10: DTU 10 MW-rapporten, s. 74
- [ ] Wöhler-eksponent for stål: avklar m = 4 eller m = 3 (DTU-rapporten bruker m = 3)
- [ ] H_s < 2 m for tilgang: finn kilde eller behold som egen antagelse
- [ ] Kjør testene (`pip install -e .[test]` og `pytest`) før pull request

### Slik sjekkes kildene

- **Tidsskriftartikler:** Åpne DOI-lenken, eller søk på tittelen i Google Scholar / Oria.
- **AMS-artikler** (J. Applied Meteorology, Monthly Weather Review): fritt tilgjengelige på journals.ametsoc.org.
- **IEC- og ISO-standarder:** Standard Norge (standard.no). Mange universiteter har tilgang via Standard Online.
- **Lærebøker:** universitetsbiblioteket, ofte som e-bok.
- **NASA- og NREL-rapporter:** gratis på ntrs.nasa.gov og nrel.gov.
- **Veileder hos MET** har trolig tilgang til flere av bøkene og standardene.
