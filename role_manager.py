"""
角色管理器 - 负责角色的创建、删除、列表等功能
"""

import json
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).parent
ROLES_DIR = BASE_DIR / "roles"
DATA_FILE = BASE_DIR / "data" / "roles.json"


def _load_roles_data() -> List[dict]:
    """加载角色数据"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_roles_data(roles: List[dict]) -> None:
    """保存角色数据"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(roles, f, ensure_ascii=False, indent=2)


def _migrate_existing_roles() -> None:
    """迁移现有角色（从名称目录改为ID目录）- 只执行一次"""
    # 检查是否已经迁移过
    migration_marker = ROLES_DIR / ".migrated"
    if migration_marker.exists():
        return

    if not ROLES_DIR.exists():
        return

    # 检查是否需要迁移（是否有以角色名命名的目录）
    needs_migration = False
    for item in ROLES_DIR.iterdir():
        # 跳过隐藏文件和标记文件
        if item.name.startswith('.'):
            continue
        if item.is_dir() and (item / "IDENTITY.md").exists():
            # 检查是否是旧结构（目录名是中文或非UUID格式）
            if not _is_uuid(item.name):
                needs_migration = True
                break

    if not needs_migration:
        # 标记为已迁移
        migration_marker.touch()
        # 确保所有角色都有注意事项字段
        _ensure_notes_field()
        return

    print("检测到旧角色结构，正在迁移...")

    # 读取现有角色
    existing_roles = []
    for item in ROLES_DIR.iterdir():
        if item.is_dir() and (item / "IDENTITY.md").exists():
            identity_file = item / "IDENTITY.md"
            with open(identity_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 从IDENTITY.md中提取角色名和描述
            name = item.name
            description = ""

            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "## 名字" in line or "## 角色名称" in line:
                    if i + 1 < len(lines):
                        name = lines[i + 1].strip()
                elif "## 角色描述" in line:
                    if i + 1 < len(lines):
                        description = lines[i + 1].strip()

            existing_roles.append({
                "name": name,
                "description": description,
                "old_dir": item.name
            })

    # 创建新结构
    new_roles = []
    for role in existing_roles:
        role_id = uuid.uuid4().hex[:12]
        new_dir = ROLES_DIR / role_id
        old_dir = ROLES_DIR / role["old_dir"]

        # 移动文件
        if old_dir.exists():
            shutil.move(str(old_dir), str(new_dir))

        # 更新IDENTITY.md为新格式（包含注意事项）
        identity_file = new_dir / "IDENTITY.md"
        if identity_file.exists():
            new_content = f"""# 角色身份

## 名字
{role['name']}

## 角色描述
{role['description']}

## 注意事项
（待填写）
"""
            with open(identity_file, "w", encoding="utf-8") as f:
                f.write(new_content)

        new_roles.append({
            "id": role_id,
            "name": role["name"],
            "description": role["description"]
        })

    _save_roles_data(new_roles)
    print(f"迁移完成，共 {len(new_roles)} 个角色")

    # 标记为已迁移
    migration_marker = ROLES_DIR / ".migrated"
    migration_marker.touch()

    # 确保所有角色都有注意事项字段
    _ensure_notes_field()


def _is_uuid(s: str) -> bool:
    """检查字符串是否是UUID格式（12位短ID）"""
    # 检查是否是12位十六进制字符串
    if len(s) != 12:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def create_role(
    name: str,
    description: str = "",
    notes: str = ""
) -> bool:
    """
    创建角色

    Args:
        name: 角色名称
        description: 角色描述
        notes: 注意事项

    Returns:
        是否创建成功
    """
    # 检查角色名是否已存在
    roles = _load_roles_data()
    for r in roles:
        if r.get("name") == name:
            print(f"角色 '{name}' 已存在")
            return False

    # 生成ID
    role_id = uuid.uuid4().hex[:12]

    # 创建角色目录
    role_dir = ROLES_DIR / role_id
    role_dir.mkdir(parents=True, exist_ok=True)

    # 创建IDENTITY.md
    identity_content = f"""# 角色身份

## 名字
{name}

## 角色描述
{description}

## 注意事项
{notes}
"""
    with open(role_dir / "IDENTITY.md", "w", encoding="utf-8") as f:
        f.write(identity_content)

    # 更新角色数据
    roles.append({
        "id": role_id,
        "name": name,
        "description": description
    })
    _save_roles_data(roles)

    print(f"角色 '{name}' 创建成功，ID: {role_id}")
    return True


def delete_role(role_id: str) -> bool:
    """
    删除角色

    Args:
        role_id: 角色ID

    Returns:
        是否删除成功
    """
    role_dir = ROLES_DIR / role_id

    if not role_dir.exists():
        print(f"角色不存在")
        return False

    # 删除角色目录
    shutil.rmtree(role_dir)

    # 更新角色数据
    roles = _load_roles_data()
    roles = [r for r in roles if r.get("id") != role_id]
    _save_roles_data(roles)

    print(f"角色已删除")
    return True


def list_roles() -> List[dict]:
    """
    列出所有角色

    Returns:
        角色列表（包含id, name, description）
    """
    # 确保迁移已完成
    _migrate_existing_roles()

    if not ROLES_DIR.exists():
        return []

    roles = _load_roles_data()
    return sorted(roles, key=lambda r: r.get("name", ""))


def get_role_by_id(role_id: str) -> Optional[dict]:
    """根据ID获取角色"""
    roles = _load_roles_data()
    for r in roles:
        if r.get("id") == role_id:
            return r
    return None


def get_role_identity(role_id: str) -> Optional[str]:
    """
    获取角色IDENTITY.md内容

    Args:
        role_id: 角色ID

    Returns:
        IDENTITY.md内容，如果不存在则返回None
    """
    identity_file = ROLES_DIR / role_id / "IDENTITY.md"

    if not identity_file.exists():
        return None

    with open(identity_file, "r", encoding="utf-8") as f:
        return f.read()


def role_exists(role_id: str) -> bool:
    """
    检查角色是否存在

    Args:
        role_id: 角色ID

    Returns:
        是否存在
    """
    identity_file = ROLES_DIR / role_id / "IDENTITY.md"
    return identity_file.exists()


# 初始化时检查并迁移（只执行一次）
_migrated = False


def _ensure_notes_field() -> None:
    """确保所有角色的IDENTITY.md都包含注意事项字段"""
    if not ROLES_DIR.exists():
        return

    for item in ROLES_DIR.iterdir():
        if not item.is_dir() or item.name.startswith('.'):
            continue

        identity_file = item / "IDENTITY.md"
        if not identity_file.exists():
            continue

        # 读取现有内容
        with open(identity_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 如果没有注意事项字段，添加它
        if "## 注意事项" not in content:
            # 在文件末尾添加注意事项
            new_content = content.rstrip() + "\n\n## 注意事项\n（待填写）\n"
            with open(identity_file, "w", encoding="utf-8") as f:
                f.write(new_content)

