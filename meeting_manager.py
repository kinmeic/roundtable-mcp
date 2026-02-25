"""
会议管理器 - 负责创建会议、运行讨论、生成会议纪要
"""

import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import llm_client
import role_manager

BASE_DIR = Path(__file__).parent
MEETINGS_DIR = BASE_DIR / "meetings"
DATA_FILE = BASE_DIR / "data" / "meetings.json"


class Meeting:
    """会议类"""

    def __init__(
        self,
        meeting_id: str,
        topic: str,
        role_ids: List[str],
        rounds: int = 3,
        status: str = "created"
    ):
        self.meeting_id = meeting_id
        self.topic = topic
        self.role_ids = role_ids
        self.role_names = []  # 角色名称列表
        self.rounds = rounds
        self.status = status
        self.discussion = []  # 讨论记录（仅在运行时使用）
        self.consensus = None  # 共识结果
        self.conclusion = None  # 结论
        self.created_at = datetime.now().isoformat()

    @property
    def roles(self) -> List[str]:
        """兼容属性，返回role_ids"""
        return self.role_ids

    def to_dict(self) -> dict:
        """转换为字典（仅包含元数据）"""
        return {
            "meeting_id": self.meeting_id,
            "topic": self.topic,
            "role_ids": self.role_ids,
            "role_names": self.role_names,
            "rounds": self.rounds,
            "status": self.status,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Meeting":
        """从字典创建"""
        meeting = cls(
            meeting_id=data["meeting_id"],
            topic=data["topic"],
            role_ids=data.get("role_ids", []),
            rounds=data.get("rounds", 3),
            status=data.get("status", "created")
        )
        meeting.role_names = data.get("role_names", [])
        return meeting


def _load_meetings_data() -> List[dict]:
    """加载会议元数据列表"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_meetings_data(meetings: List[dict]) -> None:
    """保存会议元数据列表"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meetings, f, ensure_ascii=False, indent=2)


def _update_meeting_metadata(meeting: Meeting) -> None:
    """更新会议元数据"""
    meetings = _load_meetings_data()
    for i, m in enumerate(meetings):
        if m["meeting_id"] == meeting.meeting_id:
            meetings[i] = meeting.to_dict()
            break
    _save_meetings_data(meetings)


def _get_meeting_metadata(meeting_id: str) -> Optional[dict]:
    """获取会议元数据"""
    meetings = _load_meetings_data()
    for m in meetings:
        if m["meeting_id"] == meeting_id:
            return m
    return None


def create_meeting(topic: str, role_ids: List[str], rounds: int = 3) -> Optional[Meeting]:
    """
    创建会议

    Args:
        topic: 会议主题
        role_ids: 参与角色ID列表
        rounds: 每角色发言次数

    Returns:
        会议对象，如果创建失败返回None
    """
    # 验证角色是否存在，并获取角色名称
    role_names = []
    for role_id in role_ids:
        if not role_manager.role_exists(role_id):
            print(f"角色ID '{role_id}' 不存在")
            return None
        role_info = role_manager.get_role_by_id(role_id)
        if role_info:
            role_names.append(role_info['name'])

    # 生成会议ID
    meeting_id = uuid.uuid4().hex[:12]

    # 创建会议（存储role_ids和role_names）
    meeting = Meeting(meeting_id, topic, role_ids, rounds, "created")
    meeting.role_ids = role_ids
    meeting.role_names = role_names

    # 保存元数据
    meetings = _load_meetings_data()
    meetings.append({
        "meeting_id": meeting_id,
        "topic": topic,
        "role_ids": role_ids,
        "role_names": role_names,
        "rounds": rounds,
        "status": "created"
    })
    _save_meetings_data(meetings)

    # 创建初始会议文件
    generate_meeting_minutes(meeting)

    print(f"会议创建成功，ID: {meeting_id}")
    print(f"主题: {topic}")
    print(f"参与角色: {', '.join(meeting.role_names)}")
    print(f"每角色发言次数: {rounds}")

    return meeting


def get_meeting(meeting_id: str) -> Optional[Meeting]:
    """
    获取会议

    Args:
        meeting_id: 会议ID

    Returns:
        会议对象，如果不存在返回None
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        return None
    return Meeting.from_dict(metadata)


def list_meetings() -> List[Meeting]:
    """
    列出所有会议

    Returns:
        会议列表
    """
    meetings = _load_meetings_data()
    return [Meeting.from_dict(m) for m in meetings]


def run_meeting(meeting_id: str, previous_topic: str = None, previous_conclusion: str = None, silent: bool = False) -> bool:
    """
    运行会议

    Args:
        meeting_id: 会议ID
        previous_topic: 上次会议的主题（用于继续讨论时参考）
        previous_conclusion: 上次会议的结论（用于继续讨论时参考）
        silent: 是否静默运行（不输出日志）

    Returns:
        是否成功
    """
    # 静默输出函数
    def log(*args, **kwargs):
        if not silent:
            print(*args, **kwargs)

    # 获取会议元数据
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        log("会议不存在，请重新创建")
        return False

    meeting = Meeting.from_dict(metadata)

    log(f"\n{'='*50}")
    log(f"开始会议: {meeting.topic}")
    log(f"{'='*50}\n")

    # 创建LLM客户端
    client = llm_client.create_client()
    tools = llm_client.get_default_tools()

    # 打乱角色顺序（每轮随机）
    role_order = meeting.role_ids.copy()
    random.shuffle(role_order)

    # 讨论过程
    discussion_summary = ""
    consensus_reached = False

    for round_num in range(1, meeting.rounds + 1):
        log(f"\n--- 第 {round_num} 轮 ---\n")

        round_discussion = []

        for role_id in role_order:
            # 获取角色信息
            role_info = role_manager.get_role_by_id(role_id)
            role_name = role_info['name'] if role_info else "未知角色"

            # 获取角色IDENTITY
            identity = role_manager.get_role_identity(role_id)
            if not identity:
                log(f"警告: 角色 {role_name} 的IDENTITY.md不存在")
                continue

            # 构建系统消息
            system_message = f"""你是一个角色扮演游戏的参与者。请严格按照你扮演的角色来发言。

{identity}

## 重要规则
1. 你必须严格遵守角色的设定、性格和职能
2. 在讨论中积极表达你的观点，但要与角色设定一致
3. 如果你同意其他人的观点，请明确说"我同意"
4. 如果你反对，请明确说"我反对"并说明理由
5. 尝试达成共识
6. 如果话题中涉及"今年"、"去年"、"明年"、"现在"、"当前"、"最近"等时间相关词汇，**必须先使用web_search工具搜索确认当前的具体日期和时间**，然后基于准确的时间信息进行讨论，避免使用错误的时间假设
"""

            # 构建用户消息
            if round_num == 1:
                # 如果有之前的会议信息，添加到消息中
                reference_info = ""
                if previous_topic and previous_conclusion:
                    reference_info = f"""
【参考】上次会议信息：
- 上次会议主题：{previous_topic}
- 上次会议结论：{previous_conclusion}

请结合上次会议的讨论和结论，针对以下新主题发表观点：
"""

                user_message = f"""请讨论以下主题：

{meeting.topic}
{reference_info}
请表达你的观点，并尝试与其他人达成共识。"""
            else:
                user_message = f"""请讨论以下主题：

{meeting.topic}

之前的讨论摘要：
{discussion_summary}

请在上一轮讨论的基础上继续发表你的观点，并尝试达成共识。"""

            # 调用LLM
            log(f"{role_name} 发言中...")
            try:
                response = client.call(
                    system_message=system_message,
                    user_message=user_message,
                    tools=tools,
                    temperature=0.7
                )

                content = response["text"]
                log(f"{role_name}: {content[:100]}...")

                # 记录发言
                round_discussion.append({
                    "role": role_name,
                    "content": content
                })

                # 更新讨论摘要
                discussion_summary += f"\n{role_name}: {content}"

            except Exception as e:
                log(f"调用LLM出错: {e}")
                content = f"[错误: {str(e)}]"
                round_discussion.append({
                    "role": role_name,
                    "content": content
                })

        # 本轮所有角色发言完毕，检查是否达成共识
        if _check_round_consensus(round_discussion, meeting.role_names):
            consensus_reached = True
            # 收集所有角色的最后发言作为共识
            meeting.consensus = _collect_consensus_statements(round_discussion)
            log(f"\n✓ 本轮结束，达成共识！")
        else:
            log(f"\n本轮结束，未达成共识，继续下一轮...")

        # 记录本轮讨论
        meeting.discussion.append({
            "round": round_num,
            "speeches": round_discussion
        })

        # 如果达成共识，停止讨论
        if consensus_reached:
            break

    # 生成结论
    if consensus_reached:
        meeting.conclusion = _generate_conclusion(meeting)
    else:
        meeting.conclusion = "经过多轮讨论，未能达成一致共识。"

    meeting.status = "completed"

    # 更新元数据
    _update_meeting_metadata(meeting)

    # 生成会议纪要文件
    generate_meeting_minutes(meeting)

    log(f"\n{'='*50}")
    log("会议完成！")
    log(f"{'='*50}")
    log(f"\n共识: {meeting.consensus[:200] if meeting.consensus else '未达成'}")
    log(f"\n结论: {meeting.conclusion}")

    return True


def _check_consensus(content: str) -> bool:
    """
    检查单条发言是否表示同意

    Args:
        content: 发言内容

    Returns:
        是否表示同意
    """
    content_lower = content.lower()

    # 检查是否有明确表示同意的词语
    consent_keywords = ["同意", "认可", "赞成", "支持", "我同意", "我赞成", "达成共识", "同意这个观点", "我支持"]

    for keyword in consent_keywords:
        if keyword in content_lower:
            return True

    return False


def _check_round_consensus(round_discussion: List[Dict], all_roles: List[str]) -> bool:
    """
    检查本轮是否达成共识（所有角色都同意）

    Args:
        round_discussion: 本轮讨论记录
        all_roles: 所有角色列表

    Returns:
        是否达成共识
    """
    # 检查每个角色是否都表示同意
    agreed_roles = set()

    for speech in round_discussion:
        role_name = speech["role"]
        content = speech["content"]

        if _check_consensus(content):
            agreed_roles.add(role_name)

    # 只有当所有角色都同意时才达成共识
    return agreed_roles == set(all_roles)


def _collect_consensus_statements(round_discussion: List[Dict]) -> str:
    """
    收集共识发言

    Args:
        round_discussion: 本轮讨论记录

    Returns:
        汇总的共识发言
    """
    statements = []

    for speech in round_discussion:
        role_name = speech["role"]
        content = speech["content"]
        statements.append(f"{role_name}: {content}")

    return "\n\n".join(statements)


def _generate_conclusion(meeting: Meeting) -> str:
    """
    生成结论

    Args:
        meeting: 会议对象

    Returns:
        结论文本
    """
    client = llm_client.create_client()

    # 构建讨论摘要
    discussion_text = ""
    for round_data in meeting.discussion:
        for speech in round_data["speeches"]:
            discussion_text += f"\n{speech['role']}: {speech['content']}"

    system_message = """你是一个会议总结专家。请根据讨论内容生成简洁的结论。"""

    user_message = f"""请根据以下讨论内容，生成一个简洁的结论：

主题: {meeting.topic}

讨论内容:
{discussion_text}

请生成结论："""

    try:
        response = client.call(
            system_message=system_message,
            user_message=user_message,
            temperature=0.5
        )
        return response["text"]
    except Exception as e:
        return f"结论生成失败: {str(e)}"


def generate_meeting_minutes(meeting: Meeting) -> str:
    """
    生成会议纪要文件

    Args:
        meeting: 会议对象

    Returns:
        文件路径
    """
    # 确保目录存在
    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    filename = f"{meeting.meeting_id}.md"
    filepath = MEETINGS_DIR / filename

    # 构建内容
    content = f"""# 会议纪要

## 主题
{meeting.topic}

## 参与角色
"""

    for role_name in meeting.role_names:
        content += f"- {role_name}\n"

    content += "\n## 讨论过程\n"

    # 如果有讨论记录，显示详细内容
    if meeting.discussion:
        for round_data in meeting.discussion:
            round_num = round_data["round"]
            content += f"\n### 第{round_num}轮\n"

            for speech in round_data["speeches"]:
                content += f"\n**{speech['role']}**:\n\n{speech['content']}\n"
    else:
        content += "\n（讨论进行中...）\n"

    content += "\n## 共识决策\n"

    if meeting.consensus:
        content += f"\n{meeting.consensus}\n"
    else:
        content += "\n未达成共识\n"

    content += "\n## 结论\n"
    content += f"\n{meeting.conclusion or '（待生成）'}\n"

    # 写入文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n会议纪要已保存至: {filepath}")

    return str(filepath)


def view_meeting_minutes(meeting_id: str) -> Optional[str]:
    """
    查看会议纪要

    Args:
        meeting_id: 会议ID

    Returns:
        纪要文件内容，如果不存在返回None
    """
    filepath = MEETINGS_DIR / f"{meeting_id}.md"

    if not filepath.exists():
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def continue_discussion(meeting_id: str, new_topic: str) -> bool:
    """
    继续讨论（新主题）

    Args:
        meeting_id: 会议ID
        new_topic: 新主题

    Returns:
        是否成功
    """
    meeting = get_meeting(meeting_id)
    if not meeting:
        print("会议不存在")
        return False

    # 获取之前会议的主题和结论作为参考
    previous_topic = meeting.topic

    # 从会议文件中读取之前的结论
    previous_minutes = view_meeting_minutes(meeting_id)
    previous_conclusion = None
    if previous_minutes:
        # 提取结论部分 - 找到 "## 结论" 后，收集之后所有内容
        lines = previous_minutes.split("\n")
        in_conclusion = False
        conclusion_parts = []
        for line in lines:
            # 检查是否是结论标题（支持多种格式）
            if line.strip() in ["## 结论", "## 会议结论"]:
                in_conclusion = True
                continue
            # 收集结论部分的所有内容
            if in_conclusion and line.strip():
                conclusion_parts.append(line.strip())
        if conclusion_parts:
            previous_conclusion = "\n".join(conclusion_parts)

    # 创建新的会议继续讨论
    new_meeting = create_meeting(
        topic=new_topic,
        role_ids=meeting.role_ids,
        rounds=meeting.rounds
    )

    if new_meeting:
        run_meeting(new_meeting.meeting_id, previous_topic=previous_topic, previous_conclusion=previous_conclusion)
        return True

    return False


def delete_meeting(meeting_id: str) -> bool:
    """
    删除会议

    Args:
        meeting_id: 会议ID

    Returns:
        是否删除成功
    """
    # 检查会议是否存在
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        print("会议不存在")
        return False

    # 删除会议文件
    meeting_file = MEETINGS_DIR / f"{meeting_id}.md"
    if meeting_file.exists():
        meeting_file.unlink()

    # 从元数据中删除
    meetings = _load_meetings_data()
    meetings = [m for m in meetings if m.get("meeting_id") != meeting_id]
    _save_meetings_data(meetings)

    print(f"会议已删除")
    return True


def update_meeting_topic(meeting_id: str, new_topic: str) -> bool:
    """
    更新会议主题

    Args:
        meeting_id: 会议ID
        new_topic: 新主题

    Returns:
        是否成功
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        print("会议不存在")
        return False

    metadata["topic"] = new_topic

    # 更新
    meetings = _load_meetings_data()
    for i, m in enumerate(meetings):
        if m.get("meeting_id") == meeting_id:
            meetings[i] = metadata
            break
    _save_meetings_data(meetings)

    # 更新会议文件
    generate_meeting_minutes(Meeting.from_dict(metadata))

    print(f"会议主题已更新")
    return True


def add_meeting_participant(meeting_id: str, role_id: str) -> bool:
    """
    添加会议参与者

    Args:
        meeting_id: 会议ID
        role_id: 角色ID

    Returns:
        是否成功
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        print("会议不存在")
        return False

    # 检查角色是否存在
    if not role_manager.role_exists(role_id):
        print("角色不存在")
        return False

    # 检查是否已添加
    role_ids = metadata.get("role_ids", [])
    if role_id in role_ids:
        print("角色已在会议中")
        return False

    # 添加角色
    role_ids.append(role_id)
    metadata["role_ids"] = role_ids

    # 获取角色名称
    role_info = role_manager.get_role_by_id(role_id)
    if role_info:
        role_names = metadata.get("role_names", [])
        role_names.append(role_info["name"])
        metadata["role_names"] = role_names

    # 更新
    meetings = _load_meetings_data()
    for i, m in enumerate(meetings):
        if m.get("meeting_id") == meeting_id:
            meetings[i] = metadata
            break
    _save_meetings_data(meetings)

    # 更新会议文件
    generate_meeting_minutes(Meeting.from_dict(metadata))

    print(f"已添加参与者")
    return True


def remove_meeting_participant(meeting_id: str, role_id: str) -> bool:
    """
    删除会议参与者

    Args:
        meeting_id: 会议ID
        role_id: 角色ID

    Returns:
        是否成功
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        print("会议不存在")
        return False

    # 检查是否在会议中
    role_ids = metadata.get("role_ids", [])
    if role_id not in role_ids:
        print("角色不在会议中")
        return False

    # 移除角色
    role_ids.remove(role_id)
    metadata["role_ids"] = role_ids

    # 移除角色名称
    role_info = role_manager.get_role_by_id(role_id)
    if role_info:
        role_names = metadata.get("role_names", [])
        if role_info["name"] in role_names:
            role_names.remove(role_info["name"])
        metadata["role_names"] = role_names

    # 更新
    meetings = _load_meetings_data()
    for i, m in enumerate(meetings):
        if m.get("meeting_id") == meeting_id:
            meetings[i] = metadata
            break
    _save_meetings_data(meetings)

    # 更新会议文件
    generate_meeting_minutes(Meeting.from_dict(metadata))

    print(f"已移除参与者")
    return True


def get_meeting_status(meeting_id: str) -> dict:
    """
    获取会议状态

    Args:
        meeting_id: 会议ID

    Returns:
        状态信息字典
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        return {"error": "会议不存在"}

    return {
        "meeting_id": meeting_id,
        "topic": metadata.get("topic"),
        "status": metadata.get("status"),
        "role_ids": metadata.get("role_ids", []),
        "role_names": metadata.get("role_names", []),
        "rounds": metadata.get("rounds", 3),
        "created_at": metadata.get("created_at")
    }


def update_meeting_rounds(meeting_id: str, rounds: int) -> bool:
    """
    更新会议轮次

    Args:
        meeting_id: 会议ID
        rounds: 新的轮次数

    Returns:
        是否成功
    """
    metadata = _get_meeting_metadata(meeting_id)
    if not metadata:
        print("会议不存在")
        return False

    if rounds < 1:
        print("轮次必须大于0")
        return False

    metadata["rounds"] = rounds

    # 更新
    meetings = _load_meetings_data()
    for i, m in enumerate(meetings):
        if m.get("meeting_id") == meeting_id:
            meetings[i] = metadata
            break
    _save_meetings_data(meetings)

    # 更新会议文件
    generate_meeting_minutes(Meeting.from_dict(metadata))

    print(f"会议轮次已更新为 {rounds}")
    return True
