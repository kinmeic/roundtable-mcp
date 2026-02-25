"""
命令行界面 - 提供交互式菜单
"""

import os
import sys
from typing import Optional

import config_manager
import llm_client
import meeting_manager
import role_manager


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def wait_input():
    """等待用户输入"""
    input("\n按回车键继续...")


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def print_menu(title: str, options: list):
    """
    打印菜单

    Args:
        title: 菜单标题
        options: 选项列表
    """
    print_header(title)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print()


def get_choice(max_choice: int) -> int:
    """
    获取用户选择

    Args:
        max_choice: 最大选项数

    Returns:
        用户选择的数字，0表示返回
    """
    while True:
        try:
            choice = int(input("请选择 (0-{}): ".format(max_choice)))
            if 0 <= choice <= max_choice:
                return choice
            print("无效选择，请重新输入")
        except ValueError:
            print("请输入数字")



def _analyze_and_improve_topic(topic: str) -> str:
    """
    分析并优化会议主题（流式输出）

    Args:
        topic: 原始主题

    Returns:
        优化后的主题
    """
    client = llm_client.create_client()

    system_message = """你是一个会议主题分析师。你的任务是分析用户提供的会议主题，判断其是否清晰、完整，并提供改进建议。

请分析以下方面：
1. 主题是否明确
2. 是否有遗漏的重要信息
3. 是否需要补充背景、时间、范围等要素

如果主题已经足够清晰，返回原主题。
如果需要改进，请提供改进后的主题。"""

    user_message = f"""请分析以下会议主题：

{topic}

请按以下格式回复：
1. 分析意见（指出问题）
2. 改进建议（如果有）
3. 优化后的主题（如果需要改进）

如果主题已经足够清晰，只需回复"主题清晰，无需改进："然后直接返回原主题。"""

    # 用于收集流式输出
    full_text = []
    buffer = []

    def stream_callback(text: str):
        buffer.append(text)
        # 每句话或一定长度输出一次
        if text.endswith('。') or text.endswith('！') or text.endswith('？') or len(buffer) > 5:
            print(''.join(buffer), end='', flush=True)
            full_text.extend(buffer)
            buffer.clear()

    try:
        response = client.call_stream(
            system_message=system_message,
            user_message=user_message,
            temperature=0.7,
            callback=stream_callback
        )

        # 输出剩余内容
        if buffer:
            print(''.join(buffer), end='', flush=True)
            full_text.extend(buffer)
            buffer.clear()
        print()  # 换行

        result = ''.join(full_text)

        # 检查是否需要改进
        if "无需改进" in result or "已经足够清晰" in result or "主题清晰" in result:
            return topic

        # 尝试提取改进后的主题
        lines = result.split("\n")
        improved_topic = None
        capture_next_line = False

        for line in lines:
            if "优化后" in line or "改进后" in line or "最终主题" in line:
                capture_next_line = True
                continue
            if capture_next_line and line.strip():
                improved_topic = line.strip().strip('"').strip("'")
                break

        if improved_topic and len(improved_topic) > len(topic):
            return improved_topic

        return topic

    except Exception as e:
        print(f"主题分析出错: {e}")
        return topic


def role_management_menu():
    """角色管理菜单"""
    while True:
        roles = role_manager.list_roles()
        print_menu("角色管理", [
            "创建角色",
            "删除角色",
            "列出角色",
            "查看角色详情",
            "返回主菜单"
        ])

        choice = get_choice(5)

        if choice == 0 or choice == 5:
            break
        elif choice == 1:
            create_role_interactive()
        elif choice == 2:
            delete_role_interactive()
        elif choice == 3:
            list_roles_interactive()
        elif choice == 4:
            view_role_interactive()


def create_role_interactive():
    """交互式创建角色"""
    print("\n--- 创建角色 ---\n")

    name = input("请输入角色名称: ").strip()
    if not name:
        print("角色名称不能为空")
        wait_input()
        return

    description = input("请输入角色描述: ").strip()
    if not description:
        description = "（待填写）"

    notes = input("请输入注意事项: ").strip()
    if not notes:
        notes = "（待填写）"

    role_manager.create_role(name, description, notes)
    wait_input()


def delete_role_interactive():
    """交互式删除角色"""
    roles = role_manager.list_roles()

    if not roles:
        print("\n暂无角色")
        wait_input()
        return

    print("\n--- 删除角色 ---\n")
    for i, role in enumerate(roles, 1):
        print(f"  {i}. [{role['id']}] {role['name']} - {role.get('description', '')}")

    try:
        choice = int(input("\n请选择要删除的角色 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(roles):
            role = roles[choice - 1]
            confirm = input(f"确认删除角色 '{role['name']}' 吗? (y/n): ")
            if confirm.lower() == 'y':
                role_manager.delete_role(role['id'])
    except ValueError:
        pass

    wait_input()


def list_roles_interactive():
    """交互式列出角色"""
    roles = role_manager.list_roles()

    print("\n--- 角色列表 ---\n")

    if not roles:
        print("暂无角色")
    else:
        for role in roles:
            print(f"  [{role['id']}] {role['name']} - {role.get('description', '')}")

    wait_input()


def view_role_interactive():
    """交互式查看角色详情"""
    roles = role_manager.list_roles()

    if not roles:
        print("\n暂无角色")
        wait_input()
        return

    print("\n--- 查看角色 ---\n")
    for i, role in enumerate(roles, 1):
        print(f"  {i}. [{role['id']}] {role['name']} - {role.get('description', '')}")

    try:
        choice = int(input("\n请选择要查看的角色 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(roles):
            role = roles[choice - 1]
            identity = role_manager.get_role_identity(role['id'])

            print(f"\n--- [{role['id']}] {role['name']} ---\n")
            print(identity)
    except ValueError:
        pass

    wait_input()


def meeting_management_menu():
    """会议管理菜单"""
    while True:
        print_menu("会议管理", [
            "创建会议",
            "列出会议",
            "启动会议",
            "查看会议纪要",
            "继续讨论",
            "删除会议",
            "返回主菜单"
        ])

        choice = get_choice(7)

        if choice == 0 or choice == 7:
            break
        elif choice == 1:
            create_meeting_interactive()
        elif choice == 2:
            list_meetings_interactive()
        elif choice == 3:
            start_meeting_interactive()
        elif choice == 4:
            view_meeting_interactive()
        elif choice == 5:
            continue_discussion_interactive()
        elif choice == 6:
            delete_meeting_interactive()


def delete_meeting_interactive():
    """交互式删除会议"""
    meetings = meeting_manager.list_meetings()

    if not meetings:
        print("\n暂无会议")
        wait_input()
        return

    print("\n--- 删除会议 ---\n")
    for i, m in enumerate(meetings, 1):
        status = "已完成" if m.status == "completed" else "未完成"
        print(f"  {i}. [{m.meeting_id}] {m.topic} ({status})")

    try:
        choice = int(input("\n请选择要删除的会议 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(meetings):
            meeting = meetings[choice - 1]
            confirm = input(f"确认删除会议 '{meeting.topic}' 吗? (y/n): ")
            if confirm.lower() == 'y':
                meeting_manager.delete_meeting(meeting.meeting_id)
    except ValueError:
        pass

    wait_input()


def create_meeting_interactive():
    """交互式创建会议"""
    roles = role_manager.list_roles()

    if len(roles) < 2:
        print("\n需要至少2个角色才能创建会议")
        wait_input()
        return

    print("\n--- 创建会议 ---\n")

    topic = input("请输入会议主题: ").strip()
    if not topic:
        print("会议主题不能为空")
        wait_input()
        return

    # AI分析主题
    print("\n正在分析主题...")
    improved_topic = _analyze_and_improve_topic(topic)

    if improved_topic != topic:
        print(f"\n=== 主题分析 ===")
        print(f"原主题: {topic}")
        print(f"优化后: {improved_topic}")
        confirm = input("\n是否使用优化后的主题? (y/n): ")
        if confirm.lower() == 'y':
            topic = improved_topic
        else:
            print("使用原主题")

    # 选择角色
    print("\n可用角色:")
    for i, role in enumerate(roles, 1):
        desc = role.get('description', '')
        print(f"  {i}. [{role['id']}] {role['name']} - {desc}")

    selected_roles = []
    print("\n请输入参与角色的编号（用逗号分隔，如1,2,3），输入完成后按回车:")

    while True:
        role_input = input("选择角色: ").strip()
        if not role_input:
            break

        try:
            indices = [int(x.strip()) for x in role_input.split(",")]
            for idx in indices:
                if 1 <= idx <= len(roles):
                    role = roles[idx - 1]
                    role_id = role['id']
                    if role_id not in selected_roles:
                        selected_roles.append(role_id)

            if selected_roles:
                break
        except ValueError:
            pass

        print("无效输入，请重新输入")

    if len(selected_roles) < 2:
        print("至少需要选择2个角色")
        wait_input()
        return

    # 设置发言轮次
    try:
        rounds = int(input("\n请输入每角色发言次数 (默认3): ").strip() or "3")
    except ValueError:
        rounds = 3

    meeting_manager.create_meeting(topic, selected_roles, rounds)
    wait_input()


def list_meetings_interactive():
    """交互式列出会议"""
    meetings = meeting_manager.list_meetings()

    print("\n--- 会议列表 ---\n")

    if not meetings:
        print("暂无会议")
    else:
        for m in meetings:
            status = "已完成" if m.status == "completed" else "未完成"
            print(f"  - [{m.meeting_id}] {m.topic} ({status})")

    wait_input()


def start_meeting_interactive():
    """交互式启动会议"""
    meetings = meeting_manager.list_meetings()

    # 只显示未完成的会议
    pending_meetings = [m for m in meetings if m.status != "completed"]

    if not pending_meetings:
        print("\n没有待开始的会议")
        wait_input()
        return

    print("\n--- 启动会议 ---\n")
    for i, m in enumerate(pending_meetings, 1):
        print(f"  {i}. {m.topic}")

    try:
        choice = int(input("\n请选择要启动的会议 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(pending_meetings):
            meeting = pending_meetings[choice - 1]
            print(f"\n开始会议: {meeting.topic}")
            meeting_manager.run_meeting(meeting.meeting_id)
    except ValueError:
        pass

    wait_input()


def view_meeting_interactive():
    """交互式查看会议纪要"""
    meetings = meeting_manager.list_meetings()

    if not meetings:
        print("\n暂无会议")
        wait_input()
        return

    print("\n--- 查看会议纪要 ---\n")
    for i, m in enumerate(meetings, 1):
        print(f"  {i}. [{m.meeting_id}] {m.topic}")

    try:
        choice = int(input("\n请选择要查看的会议 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(meetings):
            meeting = meetings[choice - 1]
            content = meeting_manager.view_meeting_minutes(meeting.meeting_id)

            if content:
                print(f"\n--- {meeting.topic} ---\n")
                print(content)
            else:
                print("会议纪要文件不存在")
    except ValueError:
        pass

    wait_input()


def continue_discussion_interactive():
    """交互式继续讨论"""
    meetings = meeting_manager.list_meetings()

    # 只显示已完成的会议
    completed_meetings = [m for m in meetings if m.status == "completed"]

    if not completed_meetings:
        print("\n没有已完成的会议")
        wait_input()
        return

    print("\n--- 继续讨论 ---\n")
    for i, m in enumerate(completed_meetings, 1):
        print(f"  {i}. [{m.meeting_id}] {m.topic}")

    try:
        choice = int(input("\n请选择要继续讨论的会议 (0取消): "))
        if choice == 0:
            return
        if 1 <= choice <= len(completed_meetings):
            meeting = completed_meetings[choice - 1]

            new_topic = input("请输入新主题: ").strip()
            if new_topic:
                meeting_manager.continue_discussion(meeting.meeting_id, new_topic)
            else:
                print("新主题不能为空")
    except ValueError:
        pass

    wait_input()


def config_menu():
    """配置菜单"""
    while True:
        config = config_manager.load_config()
        mcp_config = config_manager.load_mcp_config()

        print_menu("系统配置", [
            f"API密钥: {'已设置' if config.get('apiKey') else '未设置'}",
            f"模型: {config.get('model', 'MiniMax-M2.5')}",
            f"API地址: {config.get('baseUrl', '')}",
            f"MCP服务器: {len(mcp_config.get('mcpServers', {}))}个",
            "返回主菜单"
        ])

        choice = get_choice(5)

        if choice == 0 or choice == 5:
            break
        elif choice == 1:
            api_key = input("请输入API密钥: ").strip()
            if api_key:
                config["apiKey"] = api_key
                config_manager.save_config(config)
                print("API密钥已保存")
        elif choice == 2:
            model = input("请输入模型名称: ").strip()
            if model:
                config["model"] = model
                config_manager.save_config(config)
                print("模型已保存")

        wait_input()


def main_menu():
    """主菜单"""
    while True:
        print_menu("圆桌会议系统", [
            "角色管理",
            "会议管理",
            "系统配置",
            "退出"
        ])

        choice = get_choice(4)

        if choice == 0 or choice == 4:
            print("\n再见!")
            break
        elif choice == 1:
            role_management_menu()
        elif choice == 2:
            meeting_management_menu()
        elif choice == 3:
            config_menu()


def run():
    """运行主程序"""
    clear_screen()
    print("\n欢迎使用圆桌会议系统!")
    print("=" * 50)

    main_menu()


if __name__ == "__main__":
    run()
