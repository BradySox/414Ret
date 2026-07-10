import CampaignStatusBar from "./components/campaignstatus";
import EventsFeed from "./components/eventsfeed";
import MapLegend from "./components/legend/MapLegend";
import LiberationMap from "./components/liberationmap";
import useEventStream from "./hooks/useEventSteam";
import useInitialGameState from "./hooks/useInitialGameState";

function App() {
  useInitialGameState();
  useEventStream();

  return (
    <div className="App">
      <CampaignStatusBar />
      <EventsFeed />
      <MapLegend />
      <LiberationMap />
    </div>
  );
}

export default App;
