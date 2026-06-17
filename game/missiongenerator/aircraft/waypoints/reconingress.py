from .pydcswaypointbuilder import PydcsWaypointBuilder


class ReconIngressBuilder(PydcsWaypointBuilder):
    """Ingress builder for photo-recon overflights (F-14 TARPS).

    Deliberately inherits the base ``add_tasks`` (AI despawn handling only) and
    adds no attack tasks. The strike ingress builder generates Bombing tasks on
    the ingress point for every unit in the target group; a recon bird carries no
    ordnance, so those tasks would make the AI fly an aborting attack pattern
    instead of a clean overflight. The actual overflight is handled by a flyover
    TARGET_GROUP_LOC waypoint (see ``WaypointBuilder.recon_area``).
    """
