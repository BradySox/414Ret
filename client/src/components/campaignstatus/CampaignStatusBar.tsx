import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import "./CampaignStatusBar.css";
import { useState } from "react";

// The campaign-status ribbon: a slim bar above the map with the campaign name,
// turn, and date, plus the enemy-C2 chip, the HVT countdown, the VICTORY
// checklist expander, and the LAST TURN sitrep. Renders nothing when no game is
// loaded; each segment self-hides when its data is absent, so the ribbon
// degrades gracefully to just "campaign · turn · date".
//
// The VICTORY chip unfolds a checklist expander (win rows + defeat risks) —
// "where am I in the war."
//
// It floats over the Leaflet map as a plain positioned div (NOT a Leaflet
// control/layer, so the map-layer tests and z-index stack are untouched).

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
        {status.red_c2 != null && (
          <span className="campaign-status-group campaign-status-group-enemy">
            <span
              className="campaign-status-c2"
              title="Enemy command-network status (claimed) — bombing HQs makes its planning sloppier"
            >
              C2 {status.red_c2}
            </span>
          </span>
        )}
      </div>
      {expanded && victory.length > 0 && (
        <div className="campaign-status-panel">
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
