KNOWN_PREFIXES = (
    "std_msgs/msg/",
    "geometry_msgs/msg/",
    "sensor_msgs/msg/",
    "nav_msgs/msg/",
    "builtin_interfaces/msg/",
    "tf2_msgs/msg/",
    "trajectory_msgs/msg/",
    "diagnostic_msgs/msg/",
)

def is_known_ros_type(type_name: str) -> bool:
    return type_name.startswith(KNOWN_PREFIXES)