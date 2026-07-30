from __future__ import annotations
from typing import Dict, Any

def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def decode_log_data_generic(topic: str, msg: Any) -> Dict[str, Any]:
    """
    Decoder for crazyflie_interfaces/msg/LogDataGeneric.

    Tries common shapes:
    - msg.values (array)
    - msg.data (array)
    - msg.names + values
    - fallback: inspect numeric arrays and map by topic defaults
    """
    out: Dict[str, Any] = {}

    # -------- extract array ----------
    arr = None
    if hasattr(msg, "values"):
        arr = list(getattr(msg, "values"))
    elif hasattr(msg, "data"):
        arr = list(getattr(msg, "data"))

    if arr is None:
        return out

    arr = [_to_float(x) for x in arr]

    # -------- if names exist, use them ----------
    if hasattr(msg, "names"):
        names = list(getattr(msg, "names"))
        if len(names) == len(arr):
            for k, v in zip(names, arr):
                out[str(k)] = v
            return out

    # -------- topic-specific mappings ----------
    t = topic.lower()

    # imu_acc usually 3 axes
    if "/imu_acc" in t and len(arr) >= 3:
        out["ax"] = arr[0]
        out["ay"] = arr[1]
        out["az"] = arr[2]
        for i in range(3, len(arr)):
            out[f"extra_{i}"] = arr[i]
        return out

    # gyro usually 3 axes
    if "/gyro" in t and len(arr) >= 3:
        out["gx"] = arr[0]
        out["gy"] = arr[1]
        out["gz"] = arr[2]
        for i in range(3, len(arr)):
            out[f"extra_{i}"] = arr[i]
        return out

    # motors often 4 values
    if "/motors" in t and len(arr) >= 4:
        out["m1"] = arr[0]
        out["m2"] = arr[1]
        out["m3"] = arr[2]
        out["m4"] = arr[3]
        for i in range(4, len(arr)):
            out[f"extra_{i}"] = arr[i]
        return out

    # stabilizer common order (roll, pitch, yaw, thrust) OR variants
    if "/stabilizer" in t:
        common = ["roll", "pitch", "yaw", "thrust"]
        for i, v in enumerate(arr):
            if i < len(common):
                out[common[i]] = v
            else:
                out[f"extra_{i}"] = v
        return out

    # fallback indexed
    for i, v in enumerate(arr):
        out[f"value_{i}"] = v
    return out


def decode_pose_stamped(msg: Any) -> Dict[str, Any]:
    out = {}
    try:
        p = msg.pose.position
        q = msg.pose.orientation
        out["pos_x"] = float(p.x)
        out["pos_y"] = float(p.y)
        out["pos_z"] = float(p.z)
        out["ori_x"] = float(q.x)
        out["ori_y"] = float(q.y)
        out["ori_z"] = float(q.z)
        out["ori_w"] = float(q.w)
    except Exception:
        pass
    return out


def decode_twist(msg: Any) -> Dict[str, Any]:
    out = {}
    try:
        out["lin_x"] = float(msg.linear.x)
        out["lin_y"] = float(msg.linear.y)
        out["lin_z"] = float(msg.linear.z)
        out["ang_x"] = float(msg.angular.x)
        out["ang_y"] = float(msg.angular.y)
        out["ang_z"] = float(msg.angular.z)
    except Exception:
        pass
    return out


def decode_by_type_and_topic(topic: str, type_name: str, msg: Any) -> Dict[str, Any]:
    # explicit type handlers
    if type_name == "crazyflie_interfaces/msg/LogDataGeneric":
        return decode_log_data_generic(topic, msg)

    if type_name == "geometry_msgs/msg/PoseStamped":
        return decode_pose_stamped(msg)

    if type_name == "geometry_msgs/msg/Twist":
        return decode_twist(msg)

    return {}