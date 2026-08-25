# National Postures — Research Note (§96)

**Status: RESEARCHED 2026-08-25. Data drafted, nothing wired.** The table is
[`resources/borders/national_postures.yaml`](../../../resources/borders/national_postures.yaml):
47 countries, 244 dated ranges, 84 aircraft rows, no code reads it. Wiring is its own change —
see *What the engine cannot do with this yet*.

Supersedes the handoff brief, deleted in the same change and recoverable with
`git show 6b7b4f8bf:docs/dev/design/414th-national-postures-brief.md`.
Read [`414th-neutral-border-defense-notes.md`](414th-neutral-border-defense-notes.md) first —
this note only covers the data.

## Why the table exists

§96 draws every bordering nation and derives its alignment from who holds the airfields inside
its border. What alignment does *not* answer is whether an uninvolved nation lets you through:
in 2006 Turkmenistan permitted coalition transit and Iran did not, and both were neutral. Today
that is a hand-authored `overflight:` flag per campaign zone. This table replaces it with a
date-resolved answer, so §96 works on an existing campaign with no yaml at all.

## Corrections to the brief

The brief's starter country list was written from memory and said so. Measured against the
landmaps, four of its entries are wrong. Method is in the next section.

**The copy handed to this session was one commit stale** — it predated `7d9a82b15`, which added
the pre-1991 geometry blocker and an assigned question with it. That question is answered below;
it was nearly lost when the superseded brief was deleted.

| Brief said | Measured |
|---|---|
| Afghanistan: China's strip is off the playable area | **India holds 1.03 % of the map's land** (lat 28.96–34.76, lon 72.95–74.46 — Rajasthan, Punjab, Jammu), 12× China's footprint, and the brief never lists it. China is present too, 0.08 %, at the east end of the Wakhan |
| Persian Gulf: Iran, UAE, Oman, Qatar, Bahrain, Saudi, Pakistan | **Iran, UAE, Oman only.** No Qatari, Bahraini, Saudi or Pakistani land on that map. Qatar and Bahrain are on the **Iraq** map instead |
| Normandy / Channel: France, UK, Germany | **Germany has no land on either.** The third country is **Belgium** — 2.07 % of Normandy, 12.54 % of The Channel |
| Syria map: …Cyprus, Egypt (edge) | **Saudi Arabia holds 7.15 %** — more than Israel, Lebanon and Cyprus combined — and the brief omits it. Egypt is 2 samples out of 18,339 |
| Germany CW: …Austria (verify), Luxembourg (verify) | Both confirmed, and **Sweden (3.67 %) and Switzerland (1.71 %)** are missing from the list. Sweden's share is larger than Belgium's |
| Marianas: Japan (verify extent) | **No Japanese territory.** Guam and the CNMI only, both US |

The China line needs one caveat: 0.08 % is inside the *landmap*, which is the modelled land, not
the playable boundary. The brief's claim was about the playable area, which this method does not
measure. It changes no posture call — China has no airfield there and cannot be reached.

Two further findings, both about what DCS models rather than what the maps contain:

- **Armenia and Azerbaijan are not pydcs countries.** Same hole the §96 note already records for
  Turkmenistan, Uzbekistan and Tajikistan, but on the Caucasus map — the fork's most-used
  terrain. Neither can ever fly a §96 alert flight. They are drawn and permitted only.
- **The Iraq map has 19 Iraqi airfields and Kharg. Nothing else.** Kuwait, Saudi Arabia, Jordan,
  Syria and Turkey all hold land on it and none has a field to scramble from, so every one of
  them needs the point-spawn path, not `airfield:`.

## Method — how the country list was measured

Nothing here trusts a remembered list.

1. Load each terrain's `resources/theaters/*/landmap.p` and take `inclusion_zones` — the modelled
   land, in terrain XY.
2. Sample a 161×161 grid over its bounds, keep the points inside the land.
3. Project each back to lat/lon with pydcs (`Point(x, y, terrain).latlng()`).
4. Test against Natural Earth 1:50m admin-0 (public domain), via an STRtree.

Sample counts approximate each country's share of the modelled land. A second pass ran every
terrain's `terrain.airports` through the same lookup, which answers the different and more
operational question: **can this country scramble from this map at all.**

Natural Earth is a dev-time input, downloaded and discarded — never vendored, exactly as
`tools/neutral_border_geo.py` treats its GeoJSON. `<none>` airfield results are coastal and
island fields whose point falls just outside a 1:50m coastline (Batumi, Kharg, Bodø, Beirut);
they are a resolution artifact, not a finding.

## Measured: countries per map

Share of modelled land, then airfields in that country on that map.

| Map | Countries (share % / airfields) |
|---|---|
| Afghanistan | Afghanistan 48.4/26 · Pakistan 30.1/0 · Turkmenistan 10.5/0 · Tajikistan 5.1/0 · Iran 2.8/0 · Uzbekistan 2.1/0 · India 1.0/0 · China 0.1/0 |
| Caucasus | Russia 55.5/11 · Georgia 25.0/8 · Turkey 11.6/0 · Armenia 6.7/0 · Azerbaijan 1.0/0 |
| Germany Cold War | Germany 46.8/218 · Poland 10.1/2 · Czechia 9.3/0 · France 9.0/0 · Austria 5.5/0 · Netherlands 4.8/0 · Denmark 4.0/2 · Sweden 3.7/3 · Belgium 3.5/0 · Switzerland 1.7/0 · Slovakia 0.7/0 · Luxembourg 0.4/0 · Hungary 0.2/0 · Liechtenstein 0.01/0 |
| Iraq | Saudi Arabia 35.9/0 · Iran 31.7/1 · Iraq 25.4/19 · Syria 4.5/0 · Kuwait 1.0/0 · Qatar 0.7/0 · Turkey 0.4/0 · Jordan 0.1/0 · Bahrain 0.02/0 |
| Kola | Russia 35.7/12 · Sweden 25.6/8 · Finland 23.3/8 · Norway 15.4/9 |
| Marianas (both) | Guam 54.9/5 · Northern Marianas 27.8/3 — all US |
| Nevada | USA 100/17 |
| Normandy | France 73.8/60 · UK 23.3/28 · Belgium 2.1/0 |
| Persian Gulf | Iran 84.8/16 · UAE 8.6/12 · Oman 6.5/1 |
| Sinai | Egypt 66.6/34 · Saudi Arabia 14.6/1 · Jordan 9.2/2 · Syria 4.6/3 · Israel 2.7/13 · Lebanon 1.1/1 · Palestine 0.7/0 |
| South Atlantic | Argentina 52.3/10 · Chile 39.8/5 · Falklands 3.2/3 |
| Syria | Syria 33.8/84 · Turkey 32.4/22 · Iraq 9.7/5 · Jordan 9.6/19 · Saudi Arabia 7.2/0 · Israel 2.7/43 · Lebanon 1.8/19 · Palestine 1.2/1 · Cyprus 1.0/15 · N. Cyprus 0.6/8 |
| The Channel | France 72.2/5 · UK 15.0/7 · Belgium 12.5/0 |

The two Marianas terrains read identically because the WWII theatre loads the modern Marianas
landmap — already documented at `conflicttheater.py:69`, not a new defect.

## The buckets, as applied

The test is overflight, not sympathy. France was an ally in 1973 and denied US transit anyway.

| Bucket | Test | Reference case |
|---|---|---|
| `allied` | treaty ally or basing host | Turkey 1952– (NATO, İncirlik) |
| `permissive` | grants transit without alliance | Pakistan 2001–2011 (OEF overflight, the GLOC) |
| `contested` | sometimes tolerated, sometimes denied | Pakistan 2011–2021 (post-Abbottabad) |
| `closed` | refuses transit, defends its airspace, not a belligerent | Switzerland, always |
| `hostile` | active belligerent or state of war | Argentina Apr–Jun 1982 |

The engine collapses these two ways: `allied`/`permissive` → transit allowed,
`contested`/`closed`/`hostile` → refused. Recording all five keeps the split available for the
per-side and basing logic that is not built yet.

## Two rules that decide the hard cases

**1. The posture is the one that applies to a war fought on the map where the country appears.**
Consent is conflict-specific and the table is date-keyed; where those disagree, the map wins.

- **France 1966–2009.** It left NATO's integrated command in 1966 and denied US transit for the
  1986 Libya raid, but stayed committed to Central Front defence throughout (the 1967
  Ailleret–Lemnitzer accords). France appears only on Germany Cold War, Normandy and The
  Channel — European theatres — so the table says `allied`.
- **NATO Europe, October 1973.** Every European ally but Portugal denied landing and overflight
  rights for the Israel airlift; Germany, Spain, Greece and Turkey by name. Of those, only
  **Turkey** appears on a map where a 1973 war is fought, so only Turkey carries the range
  (`contested`, 1973-10 → 1973-12). Germany's refusal is recorded here and nowhere else.

**2. The derived rule wins, and often means the table is never consulted.** A nation hosting a
campaign's airfields is aligned regardless of any posture. Two entries exist only because that
rule already handles them:

- **Cyprus** — Akrotiri and Dhekelia are UK sovereign territory inside the Cypriot polygon, so
  any campaign the UK plays flips Cyprus blue-aligned by itself.
- **Kuwait, Aug 1990 – Feb 1991** — the table says `hostile` toward the US bloc because the
  airspace was Iraq's and defended as Iraq's, but a Desert Storm campaign never asks: the fields
  are red-held.

## The timelines

Each range boundary is a named event. Ranges are `[from, to)`; an uncovered date is `closed`.

### Central Asia and South Asia

- **Pakistan** is the whole spectrum. SEATO 1954 and the Baghdad Pact 1955; the US signals
  station at Badaber outside Peshawar operated 17 Jul 1959 – 7 Jan 1970 on a ten-year lease that
  lapsed in Jul 1969, and staged the 1960 U-2 flight. The Sept 1965 arms embargo, SEATO exit in
  1972 and the 1979 Symington cut-off drop it to `contested`. The Soviet invasion makes it the
  Afghan pipeline (`permissive`, never a US combat basing host). The 1990 Pressler Amendment
  ends that. Sept 2001 restores it — blanket overflight, Shamsi and Jacobabad, the ground and air
  lines of communication. Abbottabad (May 2011), Salala (26 Nov 2011, 24 Pakistani soldiers
  killed) and the resulting supply-route closure until 3 Jul 2012 drop it back to `contested`;
  the 2021 withdrawal closes it.
  Toward the Soviet bloc it is the one `hostile` entry in Central Asia: 1979–1989 Pakistan hosted
  the war against Soviet forces and the PAF shot down Soviet and Afghan aircraft over its own
  territory.
- **Uzbekistan** is the only Central Asian state that reaches `allied` — Karshi-Khanabad (K2)
  hosted US aircraft 2001–2005. The eviction notice arrived 29 Jul 2005 after US criticism of
  the Andijan crackdown; operations ceased 21 Nov 2005. It does not go `closed`, because Germany
  kept Termez throughout, and returns to `permissive` with the Northern Distribution Network.
- **Turkmenistan** holds UN-recognised permanent neutrality (12 Dec 1995) and still permitted
  non-lethal overflight and refuelling at Ashgabat from late 2001, with a standing USAF team of
  about seven airmen. That is `permissive` as the bucket is defined, and it is why the §96 note
  cites Turkmenistan as its worked example.
- **Tajikistan** is `permissive` toward the US bloc on the French air detachment at Dushanbe —
  agreement of 8 Dec 2001, 150–300 personnel, withdrawn Oct 2014 — and `allied` toward Russia
  throughout: the 201st Military Base is Russia's largest abroad.
- **India** is the brief's omission and the most consequential one. Non-aligned to the Aug 1971
  Indo-Soviet Treaty, then firmly Soviet (`allied`, 1971–1991). It only becomes `permissive`
  toward the US bloc with LEMOA in Aug 2016, which is reciprocal logistics access, not alliance.
- **Afghanistan** is almost always the war's ground, so it derives aligned and the entry is
  mostly inert. It is recorded in full anyway.

### The Caucasus

- **Georgia** tracks its own politics: `closed` to 1994, `contested` on Partnership for Peace
  (Mar 1994), `permissive` from the Train and Equip Program (2002). Toward Russia it runs the
  other way — CIS and Russian bases (`permissive`) to the Rose Revolution, `contested` to the
  August 2008 war, `closed` after. Russia handed Akhalkalaki back 27 Jun 2007 and declared its
  troops out that November.
- **Armenia** is `allied` toward Russia on the 102nd Base at Gyumri (treaty to 2044) until
  Pashinyan froze CSTO participation in Feb 2024, then `contested`. It never rises above
  `contested` toward the US bloc.
- **Azerbaijan** granted blanket OEF overflight from Sept 2001 (`permissive`) and let the CIS
  collective security treaty lapse in Apr 1999 (`contested` toward Russia since).

### Europe

Warsaw Pact members are `allied` toward the Soviet bloc from the Pact's founding (14 May 1955)
to its dissolution (1 Jul 1991), and `closed` toward the US bloc. All then run the same three
steps: `contested`, `permissive` at Partnership for Peace (Jan 1994), `allied` at NATO accession
— Poland, Czechia and Hungary 12 Mar 1999, Slovakia 29 Mar 2004. Czechoslovakia split in Jan
1993, so the Czech and Slovak entries carry identical Pact-era ranges.

The neutrals are the interesting half, and they are what §96 is for:

- **Austria** — permanent neutrality by the Neutrality Act of 26 Oct 1955. `closed` to both, and
  it means it: it permitted coalition overflight in 1991 under a UN mandate and refused the US in
  2003 without one. Case-by-case exception is what `closed` describes.
- **Switzerland** and, through it, **Liechtenstein** — `closed` to both, the whole period.
- **Sweden** — publicly non-aligned to Partnership for Peace (9 May 1994), `permissive` after,
  `allied` from NATO accession 7 Mar 2024. The secret Cold War contingency cooperation with NATO
  documented by the 1994 Neutrality Policy Commission does not change the enforced posture: a
  border feature enforces the public one.
- **Finland** — the 1948 FCMA obliged it to resist a Western attack *through Finnish territory*,
  so it is `closed` toward both blocs, not permissive toward Moscow. PfP 9 May 1994, NATO
  4 Apr 2023.
- **Norway** and **Denmark** are NATO founders whose standing base policy bars foreign forces in
  peacetime. It has never barred transit, so both stay `allied`.

### The Middle East

- **Egypt** flips completely, twice. Soviet arms from the Sept 1955 Czech deal; `allied` toward
  Moscow 1967–1972, when Soviet units flew combat from Egyptian fields; the July 1972 expulsion
  of the advisers; the friendship treaty abrogated Mar 1976. Toward the US: `closed` until
  relations resumed 7 Nov 1973, `permissive` from the Mar 1979 peace treaty — standing blanket
  overflight and priority canal transit, which is the definition of the bucket, not alliance.
- **Syria** is `allied` toward Moscow from Tartus (1971) through the 1980 Treaty and Hmeimim
  (2015) to Assad's fall on 8 Dec 2024, then `contested`. Toward the US it is `closed`, with two
  exceptions worth having: `permissive` Aug 1990 – Apr 1991, because **Syria fought in the Desert
  Storm coalition**, and `hostile` from Sept 2014, because coalition aircraft flew Syrian
  airspace uninvited and a US F/A-18 shot down a Syrian Su-22 in June 2017.
- **Egypt and Israel were both designated Major Non-NATO Allies in 1987, and the table still
  splits them.** Israel is `allied` because US combat aircraft operate from and over it and the
  US has fought for it; Egypt is `permissive` because its consent is standing but transactional —
  unfettered overflight and expedited Suez transit, more than 36,000 US overflights across
  Afghanistan and Iraq, and no US base. The designation is not the test; basing is.
- **Iraq** runs allied → hostile → allied. Baghdad Pact member to the 14 July 1958 revolution,
  out of the Pact 24 Mar 1959, the 15-year Soviet Treaty of Friendship signed 9 Apr 1972.
  `hostile` toward the US bloc from Aug 1990 straight through the no-fly zones to May 2003 —
  Iraq contested them and fired on coalition aircraft the whole time, so there is no gap. `allied`
  under occupation, and `allied` again from Jun 2014 when the anti-ISIS coalition was invited
  back; `permissive` from the Jan 2020 parliamentary vote to expel, which never took effect.
- **Iran** is `allied` toward the US as a CENTO member hosting US intelligence sites, and turns
  in Feb 1979. Two `hostile` windows: the hostage crisis and Eagle Claw (Nov 1979 – Jan 1981),
  and Earnest Will / Praying Mantis (Jul 1987 – Aug 1988). `closed` otherwise. Toward Moscow it
  was `closed` — CENTO existed to contain the USSR — and only becomes `permissive` with the 1989
  Rafsanjani–Gorbachev arms accord.
- **Saudi Arabia** is `permissive` for most of the period and `allied` only when US combat forces
  are actually in the Kingdom: Aug 1990 to the Aug 2003 handover of Prince Sultan AB (the CAOC
  moved to Al Udeid on 28 Apr 2003), and again from Oct 2019 after Abqaiq. The Oct 1973 oil
  embargo is a short `contested` window.
- **Turkey** is `allied` with three documented breaks: the Oct 1973 refusal of landing rights, the
  Feb 1975 – Sept 1978 US arms embargo over Cyprus (Turkey suspended US operations at every base
  but İncirlik), and Mar 2003 — parliament refused the northern front on 1 March by four votes,
  and overflight was granted on 21 March.
- **Jordan**, **Israel**, **Lebanon**, and the Gulf states are in the yaml with their anchors in
  the comments. The two worth flagging: Jordan is `contested` in 1990–91 because it tilted to
  Iraq, and Oman is `allied` continuously — RAF Masirah and Salalah to 1977, then the Facilities
  Access Agreement of 21 Apr 1980, the first Gulf state to formalise access with the US.

### The South Atlantic

Not in the brief's map list; added on the DM's call, because the fork ships the terrain and 1982
is a real war on it.

- **Argentina** is `hostile` toward the US-led bloc Apr–Jun 1982. It fought the UK, and the US
  sided with the UK materially from 30 Apr 1982. It becomes `permissive` as a Major Non-NATO Ally
  in Jan 1998.
- **Chile** is the reason the entry is not simply "contested". The Kennedy Amendment arms embargo
  had been in force since 1976, and Chile nonetheless ran a long-range radar opposite Comodoro
  Rivadavia feeding the British task force minute-by-minute warning — the one window when it was
  switched off for maintenance, 8 Jun 1982, is when Sir Galahad and Sir Tristram were hit. A
  `permissive` micro-range Apr–Jun 1982 sits inside the `contested` band.

## Measured but deliberately not modelled

| Territory | Why |
|---|---|
| Palestine (Sinai 0.74 %, Syria 1.18 %) | No sovereign airspace. Israel controls it under Oslo Annex I, so Palestine can neither grant nor refuse transit. A closed zone that cannot spawn would only log a warning |
| Liechtenstein (Germany CW, 1 sample) | No armed forces; airspace policed by Switzerland. Folded into Switzerland |
| Falkland Islands, Jersey, Guernsey | UK territory; the UK entry covers them |
| Guam, Northern Marianas | US territory; the USA entry covers them |
| Northern Cyprus (Syria map, 8 airfields) | **Folded into Cyprus** (DM call 2026-08-25). One island, one polygon — a de facto entity recognised only by Turkey is not drawn as its own nation |

## Pre-1991 geometry: the blocker, and the source that clears it

The brief carried this as an assigned question — find a usable public-domain historical-boundary
source, or confirm none exists. **One exists, and it is licence-clean.**

The problem, measured by the §96 session on Red Tide (Germany CW, 1988): modern Germany is one
polygon, 6 of the campaign's 12 bases sit in what was the GDR, and the alignment rule resolves
the country on a meaningless 5-blue/6-red split. The posture table has separate `Germany` and
`GDR` entries, and separate `USSR`, `Czech Republic` and `Slovakia` entries — but Natural Earth
cannot draw a border for any of them, so those entries are unreachable until the geometry exists.

Three candidate sources, and only one survives the licence gate this tree already enforces:

| Source | Coverage | Licence | Verdict |
|---|---|---|---|
| [CShapes 2.0](https://icr.ethz.ch/data/cshapes/) | 1886–2019, a real time series, GeoJSON | **CC BY-NC-SA 4.0** | **Gated.** NonCommercial bars it outright; ShareAlike would contaminate any vertex list derived from it |
| [aourednik/historical-basemaps](https://github.com/aourednik/historical-basemaps) | world borders by year, GeoJSON | **GPL-3.0** | **Gated.** The same wall as the MIST author's repos — this tree is LGPL-3 |
| [GSHHG](https://www.soest.hawaii.edu/pwessel/gshhg/) / CIA World Data Bank II | one Cold War vintage, digitized 1972–77 | **LGPL** wrapper over **US-Government public domain** | **Usable** |

GSHHG carries WDB-II's political borders alongside its shorelines, and has been LGPL since
v2.2.2 — the same licence as this tree. The underlying WDB-II was digitized by the CIA between
1972 and 1977 and released to the public, so it is US-Government public domain, and its nominal
scale (1:3,000,000, with Europe and the Middle East at 1:1,000,000) is far finer than the
Natural Earth 1:50m used for the modern borders.

Its vintage is the point: a single 1970s snapshot covers every pre-1991 boundary the fork needs,
because each was stable across the whole era. The inner-German border stood 1949–1990,
Czechoslovakia 1918–1993, the USSR to 1991, Yugoslavia to 1992, the two Yemens 1967–1990. There
is no need for a time series.

Two caveats for whoever builds it:

- **WDB-II borders are line segments, not closed polygons**, and GMT's own documentation says
  they come in no particular order. `tools/neutral_border_geo.py` takes country polygons, so the
  segments have to be assembled into closed rings first. That is the work, not the download.
- **North and South Vietnam do not matter here.** The fork's Vietnam campaigns are
  fictional-overlay on Caucasus, which the §96 DM call put out of scope.

Until that lands, **every pre-1991 era is undrawable** and the Germany Cold War map cannot carry
§96 zones at all. The postures data is still worth having: every other campaign is post-1991.

## Measured on a map but not drawn there

Distinct from the table above: the country keeps its postures, and one specific map does not get
a zone for it.

| Country | Map | Why |
|---|---|---|
| India | Afghanistan | 1.03 % of the land, no airfield. Any alert flight is a point-spawn over Rajasthan, a very long way from anything an OEF campaign flies (DM call 2026-08-25) |

## What the engine cannot do with this yet

The table is drafted against the schema in the brief, with one clarification: **all dates are
quoted strings.** Unquoted, a bare `1965` parses as an int and `1979-02` as a YAML timestamp, in
the same field. Nothing else about the shape changed.

Four gaps between the data and §96 as built:

1. **Per-side overflight is not modelled.** The table supports a nation open to blue and closed
   to red; `NeutralBorderZone.overflight` is a single bool. The zone needs a per-side flag.
2. **Six countries in the table cannot ever defend** — Armenia, Azerbaijan, Turkmenistan,
   Uzbekistan, Tajikistan and Luxembourg are not pydcs countries. Each is marked in the yaml. Do not "fix" this with a substitute flag: it would put a wrong nation's markings and
   tooltip over real territory, which is already the standing call.
3. **No date resolver exists.** Reading `[from, to)` against a campaign start date, defaulting an
   uncovered date to `closed`, and picking the bloc — none of that is written.
4. **No test guards the table.** The draft was validated by a scratchpad script that checks the
   bucket vocabulary, quoted dates, `from < to`, non-overlapping ranges, vanilla plane ids and
   coverage of every measured country. That script should become a real test when this is wired;
   it currently reports 0 errors against 47 countries and 244 ranges.

## Open questions for the DM

1. **Does `hostile` ever differ from `closed` in v1?** Both collapse to transit-refused. The
   split is recorded faithfully but buys nothing until basing or targeting logic uses it.
2. **Do the two Marianas terrains and Nevada get a border layer?** Every country on them is the
   US, so there is no bordering nation and nothing for §96 to draw.

Two are settled (DM, 2026-08-25) and are recorded above rather than here: Northern Cyprus folds
into Cyprus, and India keeps its postures but gets no zone on the Afghanistan map.
3. **Is assembling WDB-II line segments into polygons worth a session?** It is the only path
   to a Germany Cold War border layer, and it unlocks the USSR, Czechoslovakia and Yugoslavia
   in the same pass. Nothing else on the pre-1991 list is reachable without it.

## Sources

Basing, overflight and treaty anchors, verified 2026-08-25:

- [Uzbekistan's closure of Karshi-Khanabad (CRS RS22295)](https://www.everycrsreport.com/reports/RS22295.html) · [Kicked out of K2, Air & Space Forces](https://www.airandspaceforces.com/article/0910out/)
- [Ashgabat hosts US refuelling and resupply, Eurasianet](https://eurasianet.org/turkmenistan-ashgabat-hosts-us-military-refuelling-resupply-operations) · [US military operating in Turkmenistan, Foreign Policy](https://foreignpolicy.com/2009/07/14/u-s-military-operating-in-turkmenistan/)
- [The Salala incident and Pakistan–US ties (ISSI)](https://issi.org.pk/wp-content/uploads/2014/06/1379054832_41565742.pdf) · [PAF Camp Badaber](https://en.wikipedia.org/wiki/PAF_Camp_Badaber)
- [Iraq: Turkey, the deployment of US forces (CRS RL31794)](https://www.everycrsreport.com/reports/RL31794.html) · [Turkish parliament authorizes use of airspace, VOA, 20 Mar 2003](https://www.voanews.com/a/a-13-a-2003-03-20-30-turkish-67303532/381121.html)
- [Nickel Grass, Air & Space Forces](https://www.airandspaceforces.com/article/1298nickel/) · [The Yom Kippur airlift](https://www.airandspaceforces.com/article/the-yom-kippur-airlift/)
- [US to move operations from Saudi base, CNN, 29 Apr 2003](https://www.cnn.com/2003/WORLD/meast/04/29/sprj.irq.saudi.us/) · [Prince Sultan Air Base, GlobalSecurity](https://www.globalsecurity.org/military/facility/prince-sultan.htm)
- [Breaking the strategic glass: Carter and Oman, 1977–1980 (JCWS)](https://direct.mit.edu/jcws/article/26/1/156/120953/Breaking-the-Strategic-Glass-The-Carter) · [The Carter Doctrine and US bases, MERIP](https://www.merip.org/1980/09/the-carter-doctrine-and-us-bases-in-the-middle-east/)
- [Al Udeid Air Base](https://en.wikipedia.org/wiki/Al_Udeid_Air_Base)
- [Iraq–Soviet Treaty of Friendship, 9 Apr 1972 (State Department)](https://2001-2009.state.gov/documents/organization/70891.pdf) · [Soviet perceptions of Iraq, MERIP](https://www.merip.org/1988/03/soviet-perceptions-of-iraq/)
- [Finland joins NATO as 31st Ally](https://www.nato.int/cps/en/natohq/news_213448.htm) · [NATO enlargement: Sweden and Finland (Commons Library)](https://commonslibrary.parliament.uk/research-briefings/cbp-9574/)
- [Georgia: background and US policy (CRS R45307)](https://www.congress.gov/crs-product/R45307) · [End of Russian military bases in Georgia](https://www.ca-c.org/index.php/cac/article/download/1501/1361/2749)
- [Russia's remaining leverage over Armenia, Carnegie](https://carnegieendowment.org/russia-eurasia/politika/2024/03/russias-remaining-leverage-over-armenia-is-dwindling-fast?lang=en) · [The Russian base in Armenia, RFE/RL](https://www.rferl.org/a/armenia-russian-base-gyumri-alliance-weakening-geopolitical-storm/32874563.html)
- [The French military in Dushanbe, Eurasianet](https://eurasianet.org/tajikistan-the-french-military-remains-a-welcome-presence-in-dushanbe) · [France and Tajikistan (French MFA)](https://www.diplomatie.gouv.fr/en/country-files/tajikistan/france-and-tajikistan-65072)
- [Without Chile's help we would have lost the Falklands, MercoPress](https://en.mercopress.com/2014/07/08/without-chile-s-help-we-would-have-lost-the-falklands-says-former-raf-intelligence) · [Chile–UK military deal in the Falklands war, UPI](https://www.upi.com/Archives/1985/01/24/Report-Chile-and-Britain-made-military-deal-in-Falklands-war/7927475390800/)

Boundary data: Natural Earth 1:50m admin-0 countries, public domain, via the
`nvkelso/natural-earth-vector` mirror. Not vendored.
