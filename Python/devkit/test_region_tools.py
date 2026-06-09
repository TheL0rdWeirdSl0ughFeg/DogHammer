from Regions.region_tools import (
    get_users,
    view_storage_assignments,
    create_storage_assignment
)

print(
    create_storage_assignment(
        username="AtlasUnchanged",
        volume="D",
        region_root="RegionStorage",
        filepath="Users\\AtlasUnchanged"
    )
)

print(get_users())
print(view_storage_assignments())