import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import { supplyBand } from "../../theme/mapColors";
import "./CampaignStatusBar.css";
import { useState } from "react";

// The campaign-status ribbon: a slim bar above the map with the campaign name,
// turn, date, and — on Vietnam campaigns — the political-will meters. Renders
// nothing when no game is loaded; each segment self-hides when its data is absent
// (will off, supply off), so the ribbon degrades gracefully to just
// "campaign · turn · date".
//
// The VICTORY chip unfolds a checklist expander (win rows + defeat risks) plus the
// political-will history sparkline — "where am I in the war."
//
// It floats over the Leaflet map as a plain positioned div (NOT a Leaflet
// control/layer, so the map-layer tests and z-index stack are untouched).

function WillSparkline(props: { history: [number, number, number][] }) {
  if (props.history.length < 2) {
    return null;
  }
  const width = 220;
  const height = 44;
  const points = props.history;
  const x = (i: number) => (i / (points.length - 1)) * (width - 4) + 2;
  const y = (will: number) => height - 3 - (will / 100) * (height - 6);
  const path = (idx: 1 | 2) =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p[idx])}`).join(" ");
  return (
    <svg
      width={width}
      height={height}
      className="campaign-status-sparkline"
      aria-label="Political will history"
    >
      <line x1="2" y1={y(50)} x2={width - 2} y2={y(50)} className="spark-mid" />
      <path d={path(1)} className="spark-blue" />
      <path d={path(2)} className="spark-red" />
    </svg>
  );
}

// Supply chips colour by level, not side, through the SAME banding the map's
// supply nodes and the legend use (mapColors.supplyBand) — the chip and a front
// node at the same percentage must read the same colour. (The old 35/50 bands
// tracked red intent's decision thresholds, which made identical hues mean
// different numbers on the two surfaces — 2026-07-18 UI audit.)
function supplyLevel(pct: number): string {
  return "supply-" + supplyBand(pct / 100.0);
}

export default function CampaignStatusBar() {
  const status = useAppSelector(selectCampaignStatus);
  const [expanded, setExpanded] = useState(false);
  const [sitrepOpen, setSitrepOpen] = useState(false);
  if (status == null) {
    return null;
  }
  // Parse the ISO campaign date as LOCAL, not UTC: `new Date("1968-07-15")`
  // is UTC midnight, which toLocaleDateString renders as Jul 14 in any
  // western-hemisphere zone -- the ribbon showed the day before the game date.
  const [y, m, d] = status.date.split("-").map(Number);
  const dateText =
    y && m && d
      ? new Date(y, m - 1, d).toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : status.date;
  const history = status.will_history ?? [];
  // §75 custom victory conditions: win rows + defeat risks for the expander
  // block; the VICTORY chip renders whenever any are configured.
  const victory = status.victory ?? [];
  const victoryWins = victory.filter((row) => !row.defeat);
  const victoryRisks = victory.filter((row) => row.defeat);
  const sitrepLines = status.sitrep_lines ?? [];
  return (
    <div className="campaign-status-wrap">
      <div className="campaign-status-bar">
        <span className="campaign-status-name">
          {status.campaign_name ?? "Campaign"}
        </span>
        <span className="campaign-status-item">Turn {status.turn}</span>
        <span className="campaign-status-item">{dateText}</span>
        {victory.length > 0 && (
          <button
            type="button"
            className="campaign-status-victory expandable"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            title={
              status.victory_description ??
              "Alternate victory conditions — click for the live checklist"
            }
          >
            VICTORY
            <span className="campaign-status-caret">
              {expanded ? " ▴" : " ▾"}
            </span>
          </button>
        )}
        {status.blue_supply != null && (
          <span
            className={"campaign-status-supply " + supplyLevel(status.blue_supply)}
            title="Your front supply (materiel) — a starved front recovers and deploys less"
          >
            SUPPLY {Math.round(status.blue_supply)}%
          </span>
        )}
        {status.blue_will != null && (
          <span
            className="campaign-status-will campaign-status-will-blue"
            title={
              status.blue_will_note
                ? `Last turn ${status.blue_will_note}`
                : (status.blue_will_label ?? "Washington's political will")
            }
          >
            WILL {Math.round(status.blue_will)}
          </span>
        )}
        {status.hvt_name != null && status.hvt_turns_left != null && (
          <span
            className="campaign-status-hvt"
            title={
              "A named insurgent leader is exposed — kill his convoy before " +
              "the window closes and the insurgency loses momentum. Letting " +
              "it lapse is a free miss."
            }
          >
            HVT {status.hvt_name} ·{" "}
            {`${status.hvt_turns_left} turn${
              status.hvt_turns_left === 1 ? "" : "s"
            }`}
          </span>
        )}
        {sitrepLines.length > 0 && (
          <button
            type="button"
            className="campaign-status-phase expandable"
            onClick={() => setSitrepOpen(!sitrepOpen)}
            aria-expanded={sitrepOpen}
            title="What happened last turn — the kneeboard SITREP, app-side"
          >
            LAST TURN
            <span className="campaign-status-caret">
              {sitrepOpen ? " ▴" : " ▾"}
            </span>
          </button>
        )}
        {(status.red_supply != null ||
          status.red_c2 != null ||
          status.red_will != null) && (
          <span className="campaign-status-group campaign-status-group-enemy">
            {status.red_supply != null && (
              <span
                className={
                  "campaign-status-supply " + supplyLevel(status.red_supply)
                }
                title="The enemy's front supply — bomb it and a starved enemy digs in (consolidates)"
              >
                ENEMY SUPPLY {Math.round(status.red_supply)}%
              </span>
            )}
            {status.red_c2 != null && (
              <span
                className="campaign-status-c2"
                title="Enemy command-network status (claimed) — bombing HQs makes its planning sloppier"
              >
                C2 {status.red_c2}
              </span>
            )}
            {status.red_will != null && (
              <span
                className="campaign-status-will campaign-status-will-red"
                title={
                  status.red_will_note
                    ? `Last turn ${status.red_will_note}`
                    : (status.red_will_label ?? "Hanoi's regime resolve")
                }
              >
                RESOLVE {Math.round(status.red_will)}
              </span>
            )}
          </span>
        )}
      </div>
      {expanded && (
        <div className="campaign-status-panel">
          {victory.length > 0 && (
            <div className="campaign-victory-block">
              <div className="campaign-victory-title">
                Victory conditions
                {status.victory_description != null && (
                  <span className="campaign-victory-desc">
                    {" — "}
                    {status.victory_description}
                  </span>
                )}
              </div>
              {victoryWins.length > 0 && (
                <div className="campaign-victory-group">
                  <div className="campaign-victory-caption">
                    Any one of these ends the war:
                  </div>
                  <ul className="campaign-phase-objectives">
                    {victoryWins.map((row, idx) => (
                      <li
                        key={idx}
                        className={row.met ? "objective-done" : "objective-open"}
                      >
                        <span className="objective-tick">
                          {row.met ? "✓" : "○"}
                        </span>
                        {row.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {victoryRisks.length > 0 && (
                <div className="campaign-victory-group">
                  <div className="campaign-victory-caption">Defeat if:</div>
                  <ul className="campaign-phase-objectives campaign-victory-defeat">
                    {victoryRisks.map((row, idx) => (
                      <li
                        key={idx}
                        className={
                          row.met ? "objective-defeat-met" : "objective-open"
                        }
                      >
                        <span className="objective-tick">
                          {row.met ? "✗" : "○"}
                        </span>
                        {row.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          {history.length >= 2 && (
            <div className="campaign-status-panel-will">
              <span className="campaign-status-panel-will-label">
                Will over time
              </span>
              <WillSparkline history={history} />
            </div>
          )}
          {(status.blue_will_note || status.red_will_note) && (
            <div className="campaign-status-panel-notes">
              {status.blue_will_note && (
                <div className="will-note will-note-blue">
                  WILL last turn {status.blue_will_note}
                </div>
              )}
              {status.red_will_note && (
                <div className="will-note will-note-red">
                  RESOLVE last turn {status.red_will_note}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {sitrepOpen && sitrepLines.length > 0 && (
        <div className="campaign-status-panel">
          <div className="campaign-status-sitrep-title">
            SITREP — Turn {status.sitrep_turn ?? status.turn}
          </div>
          <ul className="campaign-status-sitrep-lines">
            {sitrepLines.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
