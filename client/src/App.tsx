import CampaignStatusBar from "./components/campaignstatus";
import LiberationMap from "./components/liberationmap";
import useEventStream from "./hooks/useEventSteam";
import useInitialGameState from "./hooks/useInitialGameState";

function App() {
  useInitialGameState();
  useEventStream();

  return (
    <div className="App">
      <CampaignStatusBar />
      <LiberationMap />
    </div>
  );
}

export default App;
