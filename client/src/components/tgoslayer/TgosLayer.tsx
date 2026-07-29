import { selectTgos } from "../../api/tgosSlice";
import { useAppSelector } from "../../app/hooks";
import Tgo from "../tgos/Tgo";
import { LayerGroup } from "react-leaflet";

interface TgosLayerProps {
  categories?: string[];
  exclude?: true;
  /** Narrow to these GroupTask names (e.g. ["LORAD", "MERAD"]). Omitted or empty
   *  means "every task", NOT "no task". */
  tasks?: string[];
}

export default function TgosLayer(props: TgosLayerProps) {
  const allTgos = Object.values(useAppSelector(selectTgos).tgos);
  const categoryFilter = props.categories ?? [];
  const taskFilter = props.tasks ?? [];
  // Category first, task second — BOTH must pass. The previous version returned
  // on the task check alone, which meant (a) a task-filtered layer fell THROUGH
  // to the category check for a task-less TGO, so a single task-less `aa` site
  // drew a duplicate marker in every task layer at once, and (b) the category
  // was never enforced on a task match. `task` serializes as [name, role] — the
  // tuple-valued GroupTask enum — hence task[0].
  const tgos = allTgos.filter((tgo) => {
    const inCategory =
      categoryFilter.includes(tgo.category) === !(props.exclude ?? false);
    if (!inCategory) {
      return false;
    }
    if (taskFilter.length === 0) {
      return true;
    }
    return tgo.task != null && taskFilter.includes(tgo.task[0]);
  });
  return (
    <LayerGroup>
      {tgos.map((tgo) => {
        return <Tgo key={tgo.id} tgo={tgo} />;
      })}
    </LayerGroup>
  );
}
