import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import "./EventsFeed.css";
import { useState } from "react";

// The turn-events feed (item-5 UI): the campaign's Information messages —
// phase transitions, ROE violations, political-will moves, exhaustion banners —
// surfaced on the map instead of living only in the Qt log. Collapsed to a
// count chip by default; renders nothing when there are no recent events.
// A plain positioned div, not a Leaflet layer.
export default function EventsFeed() {
  const status = useAppSelector(selectCampaignStatus);
  const [open, setOpen] = useState(false);
  const events = status?.events ?? [];
  if (events.length === 0) {
    return null;
  }
  return (
    <div className="events-feed">
      <div className="events-feed-chip" onClick={() => setOpen(!open)}>
        Events ({events.length}) {open ? "▾" : "▴"}
      </div>
      {open && (
        <div className="events-feed-list">
          {events.map((event, idx) => (
            <div className="events-feed-entry" key={idx}>
              <div className="events-feed-title">
                <span className="events-feed-turn">T{event.turn}</span>
                {event.title}
              </div>
              {event.text && (
                <div className="events-feed-text">{event.text}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
