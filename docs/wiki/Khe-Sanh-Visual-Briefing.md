# Khe Sanh: Operation Niagara — Visual Briefing

*A picture brief for **Caucasus - Khe Sanh: Operation Niagara**. The diagrams render on GitHub and
the wiki. For the full text product — the historical intelligence assessment, kneeboard threat card,
and read-aloud brief — see **[khe-sanh-intel-assessment.md](Khe-Sanh-Intel-Assessment)**; for the
working brief-builder, the **[Campaign Briefing Handbook](Khe-Sanh-Campaign-Briefing)**.*

> 🟢🟡 **Rooted in history.** The order of battle, geography, and target priorities are the real
> siege (21 Jan – 9 Apr 1968), mapped onto the Caucasus terrain. Gameplay concessions (token MiG-17s,
> deep-rear SA-2, modern module stand-ins) are flagged. **No photographic theater map is bundled
> yet** — the schematics below stand in; a real annotated map/threat overlay can be added later.

---

## Historical imagery (1968)

*Real photographs of the siege — **public domain** US-military photos except where noted. They set
the scene; the Caucasus map is the play space. Full attribution in [Image credits](#image-credits--sources).*

![C-130 on the Khe Sanh strip amid pallets and battle smoke, 1968](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/campaigns/img/khe-sanh/khe-sanh-c130-takeoff.jpg)
<sub>**The lifeline under fire** — a C-130 on the strip amid supply pallets and smoke, 1968. *USAF (PD).*</sub>

![Marines unloading a C-130B at Khe Sanh, 1968](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/campaigns/img/khe-sanh/khe-sanh-c130-unload.jpg)
<sub>**Aerial resupply** — unloading a 772nd TAS C-130B; the period caption notes a "mortar hole in the ramp." *USAF (PD).*</sub>

![Marines offload a CH-53 at Khe Sanh, 23 January 1968](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/campaigns/img/khe-sanh/khe-sanh-ch53-offload.jpg)
<sub>**Hill resupply by helo** — offloading a CH-53, 23 Jan 1968; the kind of run the "Super Gaggle" escorted through the flak. *USMC/USN (PD).*</sub>

![The Khe Sanh airstrip, 1968](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/campaigns/img/khe-sanh/khe-sanh-airstrip-1968.jpg)
<sub>**The airstrip gauntlet** — the strip, ranged by NVA guns on the approach. *USAF (PD).*</sub>

![26th Marines in the perimeter trenches, Khe Sanh 1968](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/campaigns/img/khe-sanh/khe-sanh-marines-trenchline.jpg)
<sub>**The perimeter** — 26th Marines in the trenchline. *USMC Archives (CC BY 2.0).*</sub>

---

## The siege at a glance — 21 January 1968

Khe Sanh (Kutaisi) is **encircled**. Its only lifeline is air. Blue's relief pocket (Da Nang/Batumi
+ the carriers) is *separate* — the win is to break in along Route 9 (Operation Pegasus).

```mermaid
flowchart TB
    subgraph RING["THE SIEGE RING (NVA) — closing on Khe Sanh"]
      H["Sukhumi — the hills 881/861/558<br/>artillery + AAA on the high ground"]:::red
      R9["Senaki — Route 9 / Pegasus axis<br/>(+ token MiG-17 — gameplay)"]:::red
      LV["Kobuleti — Lang Vei<br/>PT-76 / T-54 ARMOR"]:::red
    end
    KS["★ KUTAISI = KHE SANH COMBAT BASE<br/>26th Marines · encircled · air-only resupply<br/>strength 0.25"]:::blue
    H -->|siege| KS
    R9 -->|siege| KS
    LV -->|siege| KS

    subgraph RELIEF["BLUE RELIEF POCKET (separate, to the south/east)"]
      DN["Batumi — Da Nang<br/>tac air + Pegasus staging"]:::blue
      CV["Naval-1 / Naval-2 — Yankee Station<br/>A-4 · A-6 · F-8 · RA-5 · E-2"]:::blue
      RR["Tbilisi-Lochini — deep rear<br/>F-100 · F-4 · B-52 Arc Light · EC-121 · KC-135"]:::blue
    end
    DN ==>|OPERATION PEGASUS: push up Route 9| LV
    DN ==>|link up & break the siege| R9
    CV -.air.-> KS
    RR -.Arc Light / airlift.-> KS

    classDef blue fill:#13405a,stroke:#2f8fd0,color:#eaf4ff;
    classDef red fill:#5a1622,stroke:#e0402f,color:#ffd9d2;
```

---

## The threat is flak, not missiles

No MiGs worth the name, no SAMs at the base, **no MANPADS** (none existed in 1968). You fly against
**guns** — and because there are no missiles, **medium altitude is comparatively safe.** The men who
died flew into the auto-AAA or made repeat passes.

```mermaid
flowchart LR
    A["YOUR JET"]:::hd
    A --> B["57mm — S-60 / ZSU-57-2<br/>reaches MEDIUM alt<br/>roll in from above, dive, jink out"]:::amb
    A --> C["23mm ZSU-23-4 SHILKA<br/>RADAR-directed, accurate<br/>terrain-mask, new axis"]:::amb
    A --> D["23mm ZU-23 + 12.7/14.5mm<br/>lethal LOW<br/>don't loiter low, one pass"]:::amb
    A --> E["THE AIRSTRIP GAUNTLET<br/>guns range the Khe Sanh approach"]:::amb
    A --> F["MiG-17F (token) — GUNS ONLY<br/>SA-2 (deep rear)<br/>🟡 gameplay, not history"]:::minor
    classDef hd fill:#13405a,stroke:#2f8fd0,color:#eaf4ff;
    classDef amb fill:#3a2a10,stroke:#d8a72a,color:#ffe9c2;
    classDef minor fill:#241016,stroke:#7a3a3a,color:#e8c9c4;
```

---

## Target priority — how the air war wins

```mermaid
flowchart TD
    A([Operation Niagara<br/>keep the base alive · destroy the massed NVA from the air]):::hd
    A --> B[1 · The artillery<br/>Co Roc 130/152mm + hill guns — AIR-ONLY target]:::t
    A --> C[2 · The armor at Lang Vei<br/>PT-76 / T-54 — kill before it hits the wire]:::t
    B --> D[3 · Massed infantry / assembly areas<br/>ARC LIGHT]:::t
    C --> D
    D --> E[4 · Approach trenches + supply road/bridges<br/>interdiction]:::t
    E --> F([5 · Operation Pegasus<br/>push up Route 9 · link up · break the siege]):::hd
    classDef hd fill:#13405a,stroke:#2f8fd0,color:#eaf4ff;
    classDef t fill:#241016,stroke:#e0402f,color:#ffd9d2;
```

---

## Friendly air — Operation Niagara

```mermaid
graph TD
    HQ[["OPERATION NIAGARA<br/>Marine 1st MAW · Navy TF77 · USAF 7th AF"]]:::hq

    HQ --> KS["★ Khe Sanh / Kutaisi — besieged garrison air"]:::cap
    KS --> KS1["A-1H Skyraider 'Sandy' · CAS"]:::u
    KS --> KS2["OV-10 Bronco · FAC(A) 🟡 stand-in for O-1/O-2"]:::pri
    KS --> KS3["AH-1W · gunship · UH-1H medevac"]:::u

    HQ --> DN["Batumi — Da Nang"]:::f
    DN --> DN1["A-1H Skyraider · CAS"]:::u
    DN --> DN2["F-8E Crusader · BARCAP"]:::u
    DN --> DN3["CH-53E · UH-1H · lift"]:::u

    HQ --> CV["Yankee Station carriers"]:::f
    CV --> CV1["A-4E Skyhawk · A-6E Intruder · strike/CAS"]:::pri
    CV --> CV2["F-8E · BARCAP · E-2C · RA-5C recon"]:::u

    HQ --> RR["Tbilisi-Lochini — deep rear"]:::f
    RR --> RR1["B-52H · ARC LIGHT 🟡 stand-in for B-52D"]:::pri
    RR --> RR2["F-100D · F-4E · RF-101B recon"]:::u
    RR --> RR3["EC-121D AEW · KC-135 tanker · C-130 airlift"]:::u

    classDef hq fill:#0d2b45,stroke:#2f8fd0,color:#fff;
    classDef cap fill:#16405a,stroke:#5fb0e0,color:#eaf4ff;
    classDef f fill:#13303f,stroke:#2f6f90,color:#dceaf4;
    classDef u fill:#10202a,stroke:#3a6a7a,color:#cfe2ec;
    classDef pri fill:#1a4a2a,stroke:#5fd089,color:#e8ffe8;
```

*Highlighted: the workhorses — the **FAC(A)**, the **carrier strike** (A-4/A-6), and **Arc Light**.*

---

## Image credits & sources

All historical photographs come from **Wikimedia Commons** and are **public domain** as works of the
U.S. federal government, except the perimeter trenchline (CC BY 2.0, credited). **No copyrighted
press imagery is used** (no AP/UPI/Duncan/Leroy, etc.).

| Image | Author / source | License | Wikimedia Commons file |
|---|---|---|---|
| C-130 on the strip | U.S. Air Force | Public domain | `C-130 Hercules taking off from Khe Sanh 1968.jpg` |
| Marines unload C-130B | U.S. Air Force | Public domain | `Marines unload 772nd TAS C-130B at Khe Sanh 1968.jpg` |
| Marines offload CH-53 | U.S. Marine Corps / Dept. of the Navy | Public domain | `Marines offload a CH-53 at Khe Sanh, 23 January 1968.jpg` |
| Khe Sanh airstrip | U.S. Air Force | Public domain | `Khe Sanh Airport - 1968.jpg` |
| LBJ situation-room model | White House photo — Yoichi Okamoto | Public domain | `L B Johnson Model Khe Sanh.jpeg` |
| Perimeter trenchline | USMC Archives (Flickr) | CC BY 2.0 | `26 Marines trenchline.jpg` |

Files are committed to the repo at `docs/campaigns/img/khe-sanh/`; each original is at
`https://commons.wikimedia.org/wiki/File:<file name above>`.

---

*Order of battle, geography, and priorities are the historical siege mapped to Caucasus; gameplay
concessions are flagged 🟡. Full history + read-aloud brief:
[khe-sanh-intel-assessment.md](Khe-Sanh-Intel-Assessment). Working reference:
[Campaign Briefing Handbook](Khe-Sanh-Campaign-Briefing).*


---

*This page is the online copy of [`docs/campaigns/khe-sanh-visual-briefing.md`](https://github.com/bradyccox/414Ret/blob/main/docs/campaigns/khe-sanh-visual-briefing.md) in the repo. Edit that file; the wiki is mirrored from `docs/wiki/` on merge to `main`.*
