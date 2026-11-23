# References in metocean-re (wind energy)

An overview of the sources behind the methods in `metocean_re/stats/`. For each
source, the document describes what it is used for, where in the source the
relevant equations are found, how the code compares to the source, and why that
particular method was chosen.

The references are also given in the docstrings of the code (see "Used in").

Sources marked **Status: 🔶** have not yet been checked against the original
text. All other sources have been checked against the original publication.

---

## 1. Wind profile across the rotor (`profile.py`)

### IEC 61400-12-1 – rotor-equivalent wind speed (REWS)

- **Reference:** IEC 61400-12-1:2017. *Wind energy generation systems – Part 12-1:
  Power performance measurements of electricity producing wind turbines.* Ed. 2.0.
- **Used in:** `profile.py: rotor_equivalent_wind_speed`, `wind_losses.py: wind_veer_loss`
- **Equation:** REWS = ( Σ A_i/A · (u_i cos Δφ_i)³ )^(1/3)
- **Why this one:** Power follows u³, so a plain average of the wind across the
  rotor gives the wrong energy. REWS weights each strip of the rotor by its area
  and preserves the kinetic energy flux. This is the standardised definition,
  including wind veer (cos Δφ).
- **Access:** Standard Norge (standard.no) / IEC webstore. Paid, often available
  through university libraries.
- **Status:** 🔶 ⚠️ The 2017 edition has been **superseded by IEC 61400-12-1:2022
  (Ed. 3.0)**. Which edition to cite, and whether the section numbering matches
  it, remains to be decided.

### Wagner et al. (2009)

- **Reference:** Wagner, R., Antoniou, I., Pedersen, S. M., Courtney, M. S.,
  Jørgensen, H. E. (2009). The influence of the wind speed profile on wind turbine
  performance measurements. *Wind Energy* 12(4), 348–362.
  [doi:10.1002/we.297](https://doi.org/10.1002/we.297)
- **Used in:** `profile.py: rotor_equivalent_wind_speed`
- **Where in the paper** (no section numbers, so pages and equations are used):
  - Eqs. (4)–(6), p. 351 (introduction): three definitions of "equivalent wind speed"
    - (4) U_eqM1 = Σ (A_i/A) U_i, weighted mean
    - (5) U_eqT1, as (4) with the turbulence term from Eq. (3)
    - **(6) U_eqT3 = ( Σ (A_i/A) U_i³ )^(1/3)**, same energy flux through the rotor area
  - Figure 2, p. 352: the rotor divided into horizontal segments (5 in the figure, 10 in the simulations, p. 358)
  - P. 352: Eqs. (4)–(6) assume "zero tilt and yaw errors"
  - Abstract (p. 348) and conclusion (p. 362): power correlates clearly better
    with the equivalent wind speed than with the hub-height wind speed
- **Comparison with the code:** The code uses Eq. (6) without the turbulence term
  (turbulence is handled separately in `turbulence.py`), with 20 horizontal strips.
  The form matches.
  - Wind veer (cos Δφ) is **not** included in Wagner. Direction is only mentioned
    as further work (p. 361). The veer part therefore refers to IEC 61400-12-1.
  - Tilt: Wagner assumes no tilt, and so does REWS in the code. Tilt is a separate
    loss in `wind_losses.py: power_with_tilt` and is not combined with REWS.
  - Note (p. 358): in Wagner's simulations, Eq. (4) fitted best and Eq. (6)
    worst. The authors state that this depends on the turbine controller (constant
    rotor speed and pitch). It is the u³ form, Eq. (6), that was adopted in IEC
    61400-12-1, so IEC is the main source for the formula and Wagner for the idea.
- **Why this one:** The original paper showing that hub-height wind alone is not
  enough, and proposing an equivalent wind speed over the whole rotor. The IEC
  definition builds on this work.
- **Note:** Published online in 2008, printed in volume 12 (2009), so 2009 is the
  year cited.

### Power law (interpolation between NORA3 heights)

- **Equation:** u(z) = u₁ (z/z₁)^α, α = ln(u₂/u₁) / ln(z₂/z₁)
- **Why this one:** NORA3 provides wind at many heights (10–750 m). The power law
  gives a straight line in log-log space between two heights, which fits a wind
  profile better than linear interpolation. A log profile with stability
  correction is not used here, because it would require L and z₀ and is only
  valid in the surface layer (the lowest ~50–100 m), while the rotor reaches up to 270 m.
- **Source:** Common knowledge, no source needed.

---

## 2. Atmospheric stability (`stability.py`)

Approach: the NORA3 files do not contain the turbulent fluxes needed to compute
the Obukhov length L directly. Instead, the bulk Richardson number is computed
from the temperature difference between the sea surface and the air at 50 m, and
converted to z/L using Monin-Obukhov theory. This is an established method when
only mean values (not fluxes) are available.

### Stull (1988)

- **Reference:** Stull, R. B. (1988). *An Introduction to Boundary Layer
  Meteorology.* Kluwer Academic Publishers. (Now Springer, doi:10.1007/978-94-009-3027-8)
- **Used in:** `stability.py: virtual_potential_temperature` (Sec. 1.5.1),
  `bulk_richardson` (Sec. 5.6.3)
- **Equations in the book:**
  - Sec. 1.5.1, p. 7, Eq. (1.5.1b): θ_v = θ (1 + 0.61 r), unsaturated air, r = mixing ratio [g/g]
  - Sec. 5.6.3, p. 177, Eq. (5.6.3): R_B = g Δθ_v Δz / ( θ_v [(ΔU)² + (ΔV)²] )
- **Equations in the code:** θ_v = T(1 + 0.61 q) + (g/c_p) z; Ri_b = (g/θ_v,0) Δθ_v z / u(z)²
- **Comparison with the code:**
  - Ri_b: matches. Between the sea surface (u = 0) and height z,
    (ΔU)² + (ΔV)² = u(z)² and Δz = z. The code uses θ_v at the surface as the reference θ_v.
  - θ_v: the code uses three small approximations:
    1. θ ≈ T + (g/c_p) z instead of θ = T (P₀/P)^0.286 (Eq. 1.5.1c), i.e. the dry adiabatic lapse rate.
    2. Specific humidity q instead of mixing ratio r (q ≈ r, less than 1 % difference).
    3. The humidity term is multiplied by T instead of θ. This amounts to less than 0.01 K at 50 m.
  - Note (Stull p. 177): the critical value 0.25 applies to local gradients,
    not thick layers. The code does not use a critical value, only Ri_b → z/L, so
    this does not affect the results.
- **Why this one:** θ_v accounts for both humidity and height, so that air at
  different heights can be compared by density. Humidity matters a lot over the
  sea. The bulk Ri only needs values at two levels, which is what is available.
  Stull notes that this form is the most widely used in meteorology because
  weather models provide values at discrete heights (p. 177).
- **Note:** Page numbers are from the ProQuest e-book edition.

### Bolton (1980)

- **Reference:** Bolton, D. (1980). The computation of equivalent potential
  temperature. *Monthly Weather Review* 108(7), 1046–1053.
  [doi:10.1175/1520-0493(1980)108<1046:TCOEPT>2.0.CO;2](https://doi.org/10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2)
- **Used in:** `stability.py: saturation_vapour_pressure`, `specific_humidity`
- **Equation in the code:** e_s = 6.112 exp(17.67 T / (T + 243.5)) hPa (T in °C). The code uses Pa (611.2).
- **Where in the paper:**
  - P. 1047, subsection f "Saturated vapor pressure of water", right column,
    Eq. (10): e_s(T) = 6.112 exp(17.67 T / (T + 243.5)), T in °C, e_s in mb (= hPa).
    Matches the code.
  - P. 1047, just above Eq. (10): fitted to Wexler (1976) with an accuracy of 0.1 %
    for −30 °C ≤ T ≤ 35 °C. This covers the temperatures over the North Sea.
  - P. 1047, left column, "d. Water vapor": ε = R_d/R_v = 0.6220. This is the
    constant 0.622 (and 0.378 = 1 − 0.622) in `specific_humidity`.
- **Why this one:** Simple, explicit and accurate in the relevant temperature range.
  The older Tetens formula, Eq. (8) on the same page, has a 2 % error at −30 °C.
  Bolton derived Eq. (10) as an improvement, and it is the standard choice in meteorology.
- **Access:** Freely available from AMS (journals.ametsoc.org).

### Fairall et al. (2003) – vapour pressure over seawater

- **Reference:** Fairall, C. W., Bradley, E. F., Hare, J. E., Grachev, A. A.,
  Edson, J. B. (2003). Bulk parameterization of air–sea fluxes: Updates and
  verification for the COARE algorithm. *J. Climate* 16(4), 571–591.
  [doi:10.1175/1520-0442(2003)016<0571:BPOASF>2.0.CO;2](https://doi.org/10.1175/1520-0442(2003)016%3C0571:BPOASF%3E2.0.CO;2)
- **Used in:** `stability.py: bulk_richardson` (`specific_humidity(sst, 0.98, p_0)`)
- **Where in the paper** (PDF page n = p. 570 + n):
  - Sec. 2b "COARE 2.5", p. 573: surface humidity is computed from the surface
    temperature and "the vapor pressure of seawater (0.98 times the vapor
    pressure of pure water; Kraus and Businger 1994)".
  - P. 584: "reduction in seawater vapor pressure by 2% due to salinity".
- **Comparison with the code:** Matches. The code multiplies the saturation vapour
  pressure at the sea surface temperature by 0.98, to account for salinity
  lowering the vapour pressure.
- **Limitation:** COARE uses the temperature at the very surface ("cool skin"),
  which is a few tenths of a degree colder than the water below. The code uses the
  sea surface temperature from NORA3. The effect is small.
- **Why this one:** COARE is one of the most widely used algorithms for air–sea
  fluxes, so it is a good source for the factor. The original source is the
  textbook by Kraus and Businger (1994).

### Launiainen (1995)

- **Reference:** Launiainen, J. (1995). Derivation of the relationship between the
  Obukhov stability parameter and the bulk Richardson number for flux-profile
  studies. *Boundary-Layer Meteorology* 76, 165–179.
  [doi:10.1007/BF00710895](https://doi.org/10.1007/BF00710895)
- **Used in:** `stability.py: _richardson_from_zeta`, `stability_parameter`
- **Equation in the code:** Ri_b = ζ (ln(z/z₀) − ψ_h(ζ)) / (ln(z/z₀) − ψ_m(ζ))²
- **Where in the paper:**
  - Sec. 2.1, p. 167, Eq. (2): ζ = R_z (ln z/z₀ − ψ_M)² / ( α_HN (ln z/z_T − ψ_H) ).
    The code uses the same equation, solved for Ri_b, with α_HN = 1 and z_T = z₀.
  - P. 167, below Eq. (2): α_HN ≈ 1 is used in the paper.
  - P. 167, after Eq. (2): the method used by the code, building the relationship
    for arbitrary ζ and finding ζ by "inverse mapping" from the observed R_z.
  - Sec. 2.2, p. 167: z_T ≈ z₀ (C_D ≈ C_H) is "generally true over water in
    light to moderate winds". This supports the simplification in the code.
  - Appendix, pp. 177–178: (A8) stable ψ = −bζ with b ≈ 5.2 (Webb 1970); the code
    uses 5 (Dyer). (A10)–(A11) unstable Businger-Dyer with constant 15–16;
    the code uses 16.
- **Why this one:** This is the relationship between Ri_b and z/L that follows
  from the Monin-Obukhov profiles. It cannot be solved analytically for z/L. The
  code inverts it by interpolation in a lookup table, as described in the paper,
  instead of using Launiainen's approximation formulas (4)–(11). This is equally
  accurate and easier to follow.
- **Limitation:** Sec. 2.3, p. 169: the linear form ψ = −5ζ gives too strong
  stability effects when ζ > 0.5. Launiainen recommends Holtslag and De Bruin
  (1988) for strong stability. The code uses −5ζ up to ζ = 10, so the L values in
  the "very stable" class are uncertain.

### Paulson (1970) and Dyer (1974)

- **References:**
  - Paulson, C. A. (1970). The mathematical representation of wind speed and
    temperature profiles in the unstable atmospheric surface layer. *J. Applied
    Meteorology* 9(6), 857–861.
    [doi:10.1175/1520-0450(1970)009<0857:TMROWS>2.0.CO;2](https://doi.org/10.1175/1520-0450(1970)009%3C0857:TMROWS%3E2.0.CO;2)
  - Dyer, A. J. (1974). A review of flux-profile relationships. *Boundary-Layer
    Meteorology* 7(3), 363–372. [doi:10.1007/BF00240838](https://doi.org/10.1007/BF00240838)
- **Used in:** `stability.py: psi_momentum`, `psi_heat`
- **Equations:**
  - Unstable (ζ < 0): x = (1 − 16ζ)^(1/4),
    ψ_m = 2 ln((1+x)/2) + ln((1+x²)/2) − 2 arctan x + π/2,
    ψ_h = 2 ln((1+x²)/2)
  - Stable (ζ ≥ 0): ψ_m = ψ_h = −5ζ
- **Where in Paulson** (the formulas have no equation numbers, so pages are used):
  - P. 858, Sec. 2 "Profile representations", right column: the integrated
    B-D forms ψ₁ = 2 ln[(1+x)/2] + ln[(1+x²)/2] − 2 tan⁻¹x + π/2 and
    ψ₂ = 2 ln[(1+x²)/2], with x = (1 − γ z/L)^(1/4). Both match
    `psi_momentum` and `psi_heat` exactly for unstable air.
  - P. 858: the starting point φ₁ = (1 − γ z/L)^(−1/4), φ₂ = (1 − γ z/L)^(−1/2), and
    the definition of ψ in Eq. (3).
  - P. 859, Sec. 4: "The B-D representation gives the best fit to both the
    wind and temperature profiles for γ = 16". This supports the constant 16 in the code.
  - P. 860, conclusion: B-D gives the best simultaneous fit for wind and
    temperature. The log-linear form only fits near-neutral conditions.
- **Where in Dyer** (no equation numbers, so pages are used):
  - Abstract (p. 363) and Sec. 4 "Concluding Remarks" (p. 371): recommended
    forms. Unstable: φ_M = (1 − 16 z/L)^(−1/4), φ_H = (1 − 16 z/L)^(−1/2).
    Stable: φ_M = φ_H = 1 + 5 z/L. The constants 16 and 5 match the code.
  - Dyer gives the gradient forms φ, not ψ. ψ = −5 z/L for stable air is
    obtained by integrating φ = 1 + 5 z/L (the definition of ψ in Paulson's Eq. (3)).
  - P. 371: the forms are from Dyer and Hicks (1970), Quart. J. Roy. Meteor. Soc.
    96, 715–721, which is the original source.
  - P. 371: "on the stable side, the experimental material is rather
    limited". This is consistent with Launiainen's warning about −5ζ in strong stability.
- **Note:** Paulson attributes the B-D forms to Businger (1966) and Dyer
  (unpublished); Dyer (1974) is the review paper that later summarised them.
- **Limitation:** Paulson's test (p. 859) is based on 34 profiles from Kerang,
  Australia: dry land, 0.5–16 m, unstable air only. The code applies the forms at
  50 m over the sea, which is common practice, but an extrapolation.
- **Why these:** The Businger-Dyer functions are the classic and most widely used
  stability functions, and Paulson gave the integrated form (ψ) needed for the
  profiles. Newer functions exist for very stable air (e.g. Beljaars & Holtslag
  1991), but −5ζ is standard for moderately stable air and is sufficient for a
  stability classification.

### Gryning et al. (2007) – stability classes

- **Reference:** Gryning, S.-E., Batchvarova, E., Brümmer, B., Jørgensen, H.,
  Larsen, S. (2007). On the extension of the wind profile over homogeneous terrain
  beyond the surface boundary layer. *Boundary-Layer Meteorology* 124(2), 251–268.
  [doi:10.1007/s10546-007-9166-9](https://doi.org/10.1007/s10546-007-9166-9)
- **Used in:** `stability.py: CLASS_NAMES`, `_INVERSE_L_EDGES`, `stability_class`
- **Why this one:** Classification by L is widely used in the wind energy
  literature (especially from DTU/Risø), and it was developed for wind profiles up
  to rotor height.
- **Where in the paper:**
  - Table 1, p. 260, the text below the table: "10<L<50 (very stable);
    50<L<200 (Stable); 200<L<500 (near neutral/stable); L>500 or L<−500
    (neutral); −500<L<−200 (near neutral/unstable); −200<L<−100 (unstable)
    and −100<L<−50 (very unstable)".
  - Sec. 3.1 "Data processing", p. 259: the measurements are divided into "seven
    stability classes according to the Obukhov length". Only wind above 3 m/s at 10 m is used.
- **Comparison with the code:** The five middle classes match. The two outermost
  are extended in the code: very unstable −100 < L < 0 (Gryning: −100 < L < −50) and
  very stable 0 < L < 50 (Gryning: 10 < L < 50). Whether the bounds are inclusive
  (≤) or not (<) has no practical significance.
- **Why the classes are extended to L = 0:**
  - Every time step must be assigned a class. Otherwise the most extreme cases
    drop out of `losses_by_stability`, and the shares do not sum to 100 %.
  - The closer L is to 0, the stronger the stability or instability, so these
    time steps naturally belong in the outermost classes.
  - Gryning needed reliable mean profiles per class and excluded weak winds and
    very small |L|, where Monin-Obukhov theory is unreliable. Here, time steps only
    need to be sorted.
  - Drawback: L is least certain exactly here (−5ζ is too strong in strong
    stability, see Launiainen and Dyer). With z/L limited to [−100, 10] at 50 m, L
    is never smaller than 5 m on the stable side or closer to 0 than −0.5 m on the
    unstable side.
  - **How much does the extension matter?** In the test dataset (Utsira Nord
    2020–2022, 26 304 hours), 23.4 % of the time steps fall in −50 < L < 0 and
    2.1 % in 0 < L < 10, i.e. outside Gryning's bounds. Almost two thirds of
    "very unstable" (37.3 % of the time) is therefore extension. These time steps
    mostly have weak winds (5.5 % of the energy), but high turbulence, and account
    for about 18 % of the fatigue damage on steel (m = 3). The totals do not change,
    only the distribution across classes in `plot_stability_by_month`,
    `plot_stability_effects`, `plot_losses_by_stability`, `plot_loads_by_stability`,
    `plot_obukhov_validation` and the tables. This should be kept in mind when
    comparing with Gryning or other studies. A separate class for −50 < L < 0 was
    considered but not chosen: the exact value of L is too uncertain here for such
    a split to be meaningful, while it is clear that these hours are very unstable.
- **Limitation:** The data are from land (Høvsøre, land sector, and Hamburg),
  with L measured at 10–12 m (Table 1). The code computes L from Ri_b at 50 m over
  the sea. The classification is also widely used offshore.

### Charnock (1955)

- **Reference:** Charnock, H. (1955). Wind stress on a water surface. *Quarterly
  Journal of the Royal Meteorological Society* 81(350), 639–640.
  [doi:10.1002/qj.49708135027](https://doi.org/10.1002/qj.49708135027)
- **Used in:** `stability.py`, only in the comment at `SEA_ROUGHNESS`
- **Where in the paper:** P. 639, abstract: z(0) "was largely determined by
  u*", and "g z(0)/u*² = constant". This is the Charnock relation z₀ = α u*²/g.
- **Why it is mentioned:** Explains that sea surface roughness actually increases
  with the friction velocity u*, i.e. with the wind. The physical interpretation is
  that stronger wind gives a rougher surface (waves), but Charnock does not state
  this himself. The code uses a fixed z₀ instead, since ln(z/z₀), and hence
  Ri_b → z/L, changes relatively little with z₀.
- **Sanity check:** With α ≈ 0.011 (a common value in later literature, not from
  this paper) and u* ≈ 0.4 m/s (moderate wind), z₀ ≈ 0.0002 m, which is the value
  used in the code.
- **Limitation:** Charnock's measurements are from a reservoir (1.6 × 1 km), in the
  lowest 8 m, not from the open sea. The relation has nevertheless become standard
  for the sea.

---

## 3. Turbulence (`turbulence.py`)

### IEC 61400-1:2019

- **Reference:** IEC 61400-1:2019. *Wind energy generation systems – Part 1: Design
  requirements.* Ed. 4.0.
- **Used in:** `turbulence.py: SIGMA_V_RATIO`, `SIGMA_W_RATIO`, `IEC_TI_REF`, `iec_normal_turbulence`
- **Values/equations:**
  - σ_v = 0.8 σ_u and σ_w = 0.5 σ_u (Kaimal model, Annex C), so σ_u = √(k / 0.945)
  - I_ref = 0.16 / 0.14 / 0.12 for class A / B / C (Table 1)
  - Normal turbulence model: σ₁ = I_ref (0.75 V + 5.6)
- **Why this one:** NORA3 only provides TKE, not σ_u. A ratio between the
  components is needed, and the IEC ratios are the ones used in turbine design.
  The NTM is used for comparison: is the site turbulence lower than the design class?
- **Note:** In the main text the ratios are given as minimum values
  (σ₂ ≥ 0.7 σ₁), while 0.8 and 0.5 come from the Kaimal model in the annex. For
  offshore sites, IEC 61400-3-1:2019 also has its own σ₁ formula.
- **Status:** 🔶 The NTM formula and the I_ref values are confirmed by secondary
  sources. The section number (6.3.2.3) and Annex C remain to be checked in the
  2019 edition. The 2019 edition also has class **A+ (I_ref = 0.18)**, which is
  not yet included.

### Albers (2010) and IEC 61400-12-1, Annex M – turbulence normalisation

- **References:**
  - Albers, A. (2010). Turbulence and shear normalisation of wind turbine power
    curve. *Proc. European Wind Energy Conference (EWEC) 2010*, Warsaw,
    vol. 6, pp. 4116–4123. Deutsche WindGuard Consulting GmbH.
  - See also: IEC 61400-12-1:2017, Annex M (informative annex): normalisation
    of power curves for turbulence intensity. Based on the Albers method.
- **Used in:** `turbulence.py: turbulent_power`
- **Equation in the code:** P_turb(U) = ∫ P(u) · N(u; U, σ_u) du (Gauss-Hermite quadrature)
- **Where in Albers** (PDF without printed page numbers, so PDF pages are used):
  - Sec. 3.1, Eq. (1), PDF p. 2: P_sim(v) = ∫ P_I=0(v) f(v) dv, where f(v) is
    approximated by a normal distribution given by the mean wind speed and the
    turbulence intensity ("Normal Distribution Model"). Matches the code.
  - Sec. 3.1, PDF p. 2: the main assumption that the turbine always follows the
    same power curve ("zero turbulence power curve"), because it responds within
    seconds while the wind variations occur over ~100 s.
  - Sec. 3.2 and Figure 1, PDF pp. 2–3: the zero-turbulence curve is derived in
    three steps from measured data. The first step is P ∝ v³ from cut-in to rated power.
  - Sec. 5.1, PDF pp. 4–5: the method can be used to adapt theoretical power
    curves to the turbulence at a site, for wind resource assessments. This is how
    it is used here.
  - Sec. 7, PDF p. 6: the method "shifts power curve raw data always in the right
    direction", but the effect is often underestimated when the turbulence differs
    a lot from the reference.
- **Comparison with the code:**
  - The integration (Eq. 1) matches.
  - ⚠️ The simplified u³ curve is used directly as the zero-turbulence curve,
    without Albers' adjustment to measured data (Sec. 3.2). The curve resembles
    Albers' first step (P ∝ v³), so this is a reasonable simplification, but it is
    a simplification.
  - Albers corrects for variation within 10-minute periods. The code uses σ_u from
    NORA3 TKE (model values per hour or every third hour). The principle is the
    same, but the time scale differs.
- **Why this one:** The power curve is curved, so the mean power over a time step
  with varying wind is not equal to the power at the mean wind speed. Albers'
  method is simple, works for all turbine types and has been adopted in IEC 61400-12-1.
- **Note:** Albers himself refers to IEC 61400-12-1:2005, and the method was
  proposed for the next edition of the standard, where it became Annex M in the
  2017 edition. The proceedings page numbers (4116–4123) are taken from citing sources.
- **Status:**
  - Albers: checked against the paper.
  - IEC Annex M: 🔶 Not read. Confirmed through secondary sources that the annex
    covers turbulence normalisation and is based on Albers.

---

## 4. Power and energy production (`wind_power.py`, `turbines.py`, `turbines.cfg`)

### Justus et al. (1978) – Weibull fit

- **Reference:** Justus, C. G., Hargraves, W. R., Mikhail, A., Graber, D. (1978).
  Methods for estimating wind speed frequency distributions. *J. Applied
  Meteorology* 17(3), 350–353.
  [doi:10.1175/1520-0450(1978)017<0350:MFEWSF>2.0.CO;2](https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2)
- **Used in:** `wind_power.py: fit_weibull`, `weibull_pdf`
- **Equation in the code:** k = (σ/ū)^(−1.086), c = ū / Γ(1 + 1/k)
- **Where in the paper:**
  - Sec. 2c "Mean wind speed and standard deviation – Method 3", p. 351, right
    column: Eq. (13) V̄ = c Γ(1 + 1/k), Eq. (14) the exact relationship between
    σ/V̄ and k, **Eq. (15) k = (σ/V̄)^(−1.086)** as an approximation to (14), and
    **Eq. (16) c = V̄/Γ(1 + 1/k)**. Matches the code.
  - P. 351: σ² = ⟨(V − V̄)²⟩, i.e. the population standard deviation, which is
    what `numpy.std()` returns by default.
  - P. 350, Eq. (1): the Weibull distribution. Matches `weibull_pdf`.
  - P. 352, right column: maximum likelihood (Takle and Brown 1977) is
    "potentially more accurate but somewhat more difficult to apply".
- **Why this one:** Simple and explicit (no iteration), and only needs the mean
  and standard deviation. The alternative is maximum likelihood
  (`scipy.stats.weibull_min.fit`), which can be more accurate, but is slower and
  less transparent.
- **Note:** Table 2 (p. 352) tests methods 1, 4 and 5, not method 3, so the paper
  does not give a measure of the accuracy of Eq. (15).
- **Access:** Freely available from AMS / JSTOR.

### Reference turbines (`turbines.cfg`)

Reference turbines are public turbine designs created by research institutes, so
that researchers can work with the same turbine and compare results. Six numbers
are used per turbine: rated power, cut-in, rated wind speed, cut-out, hub height
and rotor diameter.

| Turbine | Source | Table | Access |
|---|---|---|---|
| NREL 5 MW | Jonkman, J., Butterfield, S., Musial, W., Scott, G. (2009). *Definition of a 5-MW Reference Wind Turbine for Offshore System Development.* NREL/TP-500-38060. | Table 1-1 "Gross Properties", p. 2 | nrel.gov (free) |
| DTU 10 MW | Bak, C., Zahle, F., Bitsche, R., Kim, T., Yde, A., Henriksen, L. C., Natarajan, A., Hansen, M. H. (2013). *Description of the DTU 10 MW Reference Wind Turbine.* DTU Wind Energy Report-I-0092. | Table 2.1 "Key parameters", p. 13, column "DTU 10MW RWT" | orbit.dtu.dk (free) |
| IEA 15 MW | Gaertner, E. et al. (2020). *Definition of the IEA Wind 15-Megawatt Offshore Reference Wind Turbine.* NREL/TP-5000-75698. | Table 1-1 "Key Parameters", p. 5 | nrel.gov (free) |

- **Comparison with the code:** All six numbers in `turbines.cfg` match for all
  three turbines. The IEA report's table also lists the DTU 10 MW, with the same
  numbers. The sources are also given as comments in `turbines.cfg`.
- **Note:** The NREL report (p. 3) states that the 126 m diameter ignores the
  precone (2.5°), so the actual diameter is slightly smaller (less than 0.1 %).
  This is negligible.

### Simplified power curve

- **Used in:** `turbines.py: Turbine.power`
- **Model:** P ∝ u³ between cut-in and rated wind speed, constant up to cut-out.
- **Why this one:** It only needs four numbers per turbine and is easy to
  understand. The drawback is that it does not capture the decrease in C_P towards
  rated wind speed. The reference reports above contain real power curves as
  tables, which could replace the model.
- **Source:** Own simplification (assumption). Albers (2010), Figure 1, uses the
  same form (P ∝ v³ from cut-in to rated power) as the first step for a
  zero-turbulence power curve, so the form has some support.

---

## 5. Losses (`wind_losses.py`)

### ISO 2533:1975 – standard air density

- **Reference:** ISO 2533:1975. *Standard Atmosphere.*
- **Used in:** `wind_losses.py: STANDARD_AIR_DENSITY` (1.225 kg/m³)
- **Note:** The value is common knowledge.

### IEC 61400-12-1 – density correction

- **Used in:** `wind_losses.py: power_with_air_density`
- **Equation:** u_n = u (ρ/ρ₀)^(1/3) (for pitch-regulated turbines)
- **Why this one:** Power is proportional to ρu³. Scaling the wind speed instead of
  the power keeps rated power as the upper limit, which is correct for
  pitch-regulated turbines. The standard specifies this form.
- **Status:** 🔶 The section number is not yet given in the code. See also the note
  on the edition under §1.

### Holthuijsen (2007) – wavelength

- **Reference:** Holthuijsen, L. H. (2007). *Waves in Oceanic and Coastal Waters.*
  Cambridge University Press. doi:10.1017/CBO9780511618536
- **Used in:** `wind_losses.py: wave_tilt_amplitude`
- **Equation in the code:** L = g T_p² / (2π) (deep water); maximum slope = arctan(π H_s / L)
- **Where in the book** (Ch. 5 "Linear wave theory (oceanic waters)", pp. 105–143):
  - Sec. 5.4.3 "Dynamics", p. 123, Eq. (5.4.18): L₀ = g T²/(2π) (deep water).
    Matches the code. Just above is the general form for all depths, Eq. (5.4.17):
    L = g T²/(2π) · tanh(2πd/L).
  - Note 5A, p. 118: harmonic wave η = (H/2) sin(2πt/T − 2πx/L). The maximum slope
    (H/2)(2π/L) = πH/L follows directly from this (not written out in the book).
  - P. 118: linear theory assumes small amplitude (ak ≪ 2π). Sec. 5.1, p. 105:
    the theory should not be used for steep waves.
- **Why this one:** The deep-water relation is explicit and valid when the depth
  is more than about half the wavelength. With Tp = 15 s, Eq. (5.4.18) gives
  L₀ ≈ 350 m, so the depth should be above about 175 m. The water depth at Utsira
  Nord is 250–280 m (Equinor, equinor.com/no/energi/utsira-nord). With d = 250 m,
  the deep-water form (d > L/2) holds for Tp below about 18 s, i.e. practically
  all waves.
- **Limitation:** ⚠️ The book describes a regular wave with height H. Setting
  H = H_s for an irregular sea is a simplification made here and is not from the book.

### Carroll et al. (2016) – failure rate and repair time

- **Reference:** Carroll, J., McDonald, A., McMillan, D. (2016). Failure rate,
  repair time and unscheduled O&M cost analysis of offshore wind turbines.
  *Wind Energy* 19(6), 1107–1119.
  [doi:10.1002/we.1887](https://doi.org/10.1002/we.1887)
- **Used in:** `wind_losses.py: weather_maintenance_loss`, `annual_energy_losses`;
  `plots/wind_losses.py: plot_maintenance_downtime` (default values)
- **Values in the code:** 8.3 failures per turbine per year, 12 h repair time
- **Where in the paper** (PDF page n = p. 1106 + n):
  - Sec. 5.1, p. 1110: "The average failure rate for an offshore wind turbine
    from this analysis is 8.3 failures per turbine per year", split into 6.2 minor
    repairs, 1.1 major repairs and 0.3 major replacements.
  - Conclusion, p. 1117: the failure rate levels off at about 10 per turbine per
    year from the third year of operation.
  - Table II, p. 1117: failure rate and repair time per category: minor 6.81/yr and
    6.67 h, major 1.17/yr and 17.64 h, replacement 0.29/yr and 116.19 h. The table
    says "days", but the numbers must be hours (the reference column has the same
    values as Table I, where the unit is hours).
  - Sec. 5.5, p. 1115: the repair time is only the time technicians spend in the
    turbine, excluding travel time and waiting for access.
- **Comparison with the code:**
  - The failure rate of 8.3 is taken directly from the paper.
  - 12 h is Carroll's repair time weighted by failure rate:
    (6.81·6.67 + 1.17·17.64 + 0.29·116.19) / 8.27 ≈ 12.1 h.
- **Limitations:** Carroll counts as a failure any unscheduled visit where
  material is used (p. 1117), including minor faults. The code lets every failure
  stop the turbine until a weather window is found, and uses the same Hs limit for
  all, even though major replacements require other vessels (Table I). The Hs limit
  is not from Carroll.
- **Sensitivity:** For the IEA 15 MW in the test dataset, the maintenance loss is
  7.83 % with 8.3 failures/yr, compared with 5.66 % with 6 failures/yr.

### Assumptions and parameter choices

| Value / model | Used in | Basis |
|---|---|---|
| z₀ = 0.0002 m | `stability.py: SEA_ROUGHNESS` | Corresponds to the Charnock relation at moderate wind (see Charnock). |
| z₀h = z₀ | `stability.py: _richardson_from_zeta` | Launiainen (1995), Sec. 2.2: valid over the sea in light to moderate winds. |
| 8.3 failures/yr, 12 h repair | `weather_maintenance_loss`, `annual_energy_losses`, `plot_maintenance_downtime` | Carroll et al. (2016), see above. 12 h matches Carroll's weighted mean (≈ 12.1 h). |
| H_s < 2 m for access | `weather_maintenance_loss` | Own assumption. Not from Carroll (Table I only states that CTVs are used). The result is very sensitive to this value, see `plot_maintenance_downtime` (right panel). |
| Factor 0.98 for vapour pressure over seawater | `bulk_richardson` | Fairall et al. (2003), see Sec. 2. |
| Electrical loss 2 % | `electrical_loss` | Own assumption. Typical value (1–3 %). Note: the generator efficiency (94.4 % in the NREL 5 MW report) is not the same thing; it is already included in the power curve. |
| Scheduled maintenance 14 days/yr | `availability_loss` | Own assumption, set in consultation with the supervisor at MET Norway. |
| Restart below 20 m/s after storm shutdown | `power_with_hysteresis` | Own assumption. Typical value for illustration, not from a specific turbine. |
| Rotor sees u·cos θ | `power_with_tilt` | Own assumption. Simple geometry. The literature applies cos² or cos³ to the *power*, and this model corresponds to cos³ below rated wind speed. |
| Fixed tilt 5°, wave response 1.0 | `wind_losses.py`, example script | Own assumption. Scenario choices. A response of 1.0 is a deliberate upper bound. |

---

## 6. Loads (`wind_loads.py`)

### Burton et al. (2021) – actuator disc theory

- **Reference:** Burton, T., Jenkins, N., Bossanyi, E., Sharpe, D., Graham, M.
  (2021). *Wind Energy Handbook*, 3rd ed. Wiley.
  [doi:10.1002/9781119451143](https://doi.org/10.1002/9781119451143)
  (The section numbers are the same as in the 2nd edition, 2011.)
- **Used in:** `wind_loads.py: thrust_coefficient`
- **Equations in the code:** C_P = 4a(1−a)², C_T = 4a(1−a), Betz limit C_P ≤ 16/27,
  a found from C_P on 0 ≤ a ≤ 1/3
- **Where in the book** (Ch. 3 "Aerodynamics of horizontal axis wind turbines"):
  - Sec. 3.2 "The actuator disc concept", pp. 41–42, Eq. (3.2): U_D = U∞(1 − a)
  - Sec. 3.2.2, p. 43, Eq. (3.12): C_P = 4a(1 − a)²
  - Sec. 3.2.3, p. 43, Eq. (3.13): maximum at a = 1/3, C_P,max = 16/27 ≈ 0.593 (the Betz limit)
  - Sec. 3.2.4, p. 44, Eq. (3.16): C_T = 4a(1 − a)
  - P. 44, below Eq. (3.16): momentum theory does not apply for a ≥ 1/2. The code
    only uses a ≤ 1/3 and is well within this range.
- **Why this one:** Only the power curve is available, not a C_T curve. Actuator
  disc theory gives C_T from C_P via the induction factor a. This is the simplest
  physically consistent link. It underestimates C_T below rated wind speed because
  ideal theory does not include losses (stated in the docstring).

### Bendat (1964) – fatigue

- **Reference:** Bendat, J. S. (1964). *Probability functions for random responses:
  prediction of peaks, fatigue damage, and catastrophic failures.* NASA CR-33.
  [ntrs.nasa.gov/citations/19640008076](https://ntrs.nasa.gov/citations/19640008076)
- **Used in:** `wind_loads.py: relative_fatigue_damage`
- **Equation in the code:** E[S^m] = (2√2 σ)^m Γ(1 + m/2) (Rayleigh-distributed stress ranges, narrow band)
- **Where in the report** (report page number = PDF page number − 3):
  - Sec. 3 "Peak Probability Functions for Narrow Band Noise", Eqs. (27)–(28),
    report p. 12 (PDF p. 15): the peaks of narrow-band Gaussian noise are Rayleigh distributed.
  - Sec. 6 "Expected Fatigue Damage and its Variance", Eqs. (43)–(45),
    report pp. 19–20 (PDF pp. 22–23): Palmgren-Miner, damage per half-cycle d = K |S|^b.
  - Sec. 7.1 "Expected Value in Damage Estimates", Eqs. (80)–(82),
    report pp. 29–30 (PDF pp. 32–33): expected damage ∝ (√2 σ)^b Γ(1 + b/2).
- **Comparison with the code:** Bendat works with peak amplitudes, (√2 σ)^b. The
  code works with stress ranges (twice as large), (2√2 σ)^m. The difference is the
  constant 2^m, which cancels because the code only uses each time step's share of
  the total damage. The result is the same.
- **Simplifications:**
  - The same number of cycles in every time step. In Bendat, the number of
    half-cycles is m = 2N₀⁺T (Eq. 48) and depends on how often the signal crosses zero.
  - The stress is assumed proportional to the thrust, so σ = the standard deviation of the thrust.
  - Narrow band (Sec. 7.1). Real turbine loads are often more broadband.
- **Why this one:** Gives fatigue damage directly from the standard deviation,
  without a time series and rainflow counting. NORA3 does not have data at high
  enough resolution for rainflow counting.
- **Access:** Free, public NASA report.

### Assumptions and parameter choices

| Value / model | Used in | Basis |
|---|---|---|
| Wöhler exponent m = 10 (composite, blades) | `WOHLER_COMPOSITE` | DTU 10 MW report (Bak et al. 2013), Sec. 6.4.4, p. 74: "For the blade loads a Wöhler exponent of m = 10 has been used." |
| Wöhler exponent m = 3 (steel, tower) | `WOHLER_STEEL` | Same place in the DTU report: "Other components are assumed to be steel, m = 3." |
| σ_F = ρ A C_T U σ_u | `thrust_std` | Own derivation. Quasi-static linearisation (dF/du · σ_u). |
| (u_top² − u_bottom²) / u_hub² | `rotor_load_asymmetry` | Own assumption. A simple indicator, not a standard quantity. |

---

## 7. Data

- **NORA3:** Haakenstad, H., Breivik, Ø., Furevik, B. R., Reistad, M., Bohlinger,
  P., Aarnes, O. J. (2021). NORA3: A nonhydrostatic high-resolution hindcast of the
  North Sea, the Norwegian Sea, and the Barents Sea. *J. Applied Meteorology and
  Climatology* 60(10), 1443–1464.
  [doi:10.1175/JAMC-D-21-0029.1](https://doi.org/10.1175/JAMC-D-21-0029.1)
  - Covers the atmospheric data.
- **NORA3 waves:** Breivik, Ø., Carrasco, A., Haakenstad, H., Aarnes, O. J.,
  Behrens, A., Bidlot, J.-R., Björkqvist, J.-V., Bohlinger, P., Furevik, B. R.,
  Staneva, J., Reistad, M. (2022). The impact of a reduced high-wind Charnock
  parameter on wave growth with application to the North Sea, the Norwegian Sea,
  and the Arctic Ocean. *J. Geophysical Research: Oceans* 127(3), e2021JC018196.
  [doi:10.1029/2021JC018196](https://doi.org/10.1029/2021JC018196)
  - Covers the wave data (Hs, Tp) from `NORA3_wave_sub`. MET Norway's wave page
    ([ocean.met.no/waves](https://ocean.met.no/waves)) gives this as the reference
    for "The NORA3 wave hindcast (NORA3_wave)", produced with WAM 4.7.0 forced by
    NORA3 winds.
- **Used in:** `tests/data/NORA3_utsira_nord_2020_2022.csv`
- **Licence:** MET Norway's data catalogue lists CC BY 4.0 for NORA3
  ([data.met.no](https://data.met.no/dataset/ddb4c5d1-70b5-4d09-98a8-fadbf5e2d2ba)).
  CC BY requires the source to be credited, which is done here. The
  licence may differ between NORA3 products, so check the licence field for each
  product used (wind, waves, atmosphere).

---

## 8. Common knowledge (no source needed)

- Power law: u(z) = u_ref (z/z_ref)^α
- Power in the wind: P = ½ ρ A u³, and capacity factor
- Ideal gas law for moist air and the hypsometric equation
- Turbulence intensity TI = σ_u/U and TKE = ½(σ_u² + σ_v² + σ_w²)
- Mathematics: area of strips of a circle, linear interpolation, Gauss-Hermite quadrature
