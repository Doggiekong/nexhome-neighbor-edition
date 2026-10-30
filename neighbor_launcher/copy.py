"""Reviewed plain-language strings. Technical values belong only in closed details."""

from neighbor_installer.detection import Owner

SCREENS = {
    'welcome': ('欢迎使用', '让你家的 NexHome 更稳定、更方便地使用 Home Assistant。', '开始检查'),
    'fresh': ('还没有安装 NexHome', '可以在这里安装友邻加强版。安装前会先做好备份。', '开始安装'),
    'official': ('发现你已经安装了官方版 NexHome', '可以切换到友邻加强版。现有设备名称、房间和自动化会尽量保持不变。', '继续'),
    'latest': ('你已经是最新版，无需操作', '友邻加强版已安装。你可以继续使用原来的设备和设置。', '重新检查'),
    'update': ('发现新版本', '更新前会自动备份。只有你确认后才会开始。', '更新'),
    'hacs': ('你已通过 HACS 安装友邻加强版', '请继续通过 HACS 更新，这里不会另外替换它。', '重新检查'),
    'unknown': ('暂时无法确认之前的安装方式', '为了保护你现在的设备和自动化，我们不会直接覆盖它。', '查看详情'),
    'conflict': ('需要先检查安装方式', 'NexHome 可能同时被两种方式管理。为避免以后更新互相覆盖，现在先不继续。', '查看详情'),
    'confirm': ('准备好了，请确认', '开始后 Home Assistant 会短暂重启。若页面没有恢复，请重新打开安装助手查看进度，不要重复安装。', '确认并开始'),
    'running': ('正在处理，请稍候', '请保留这个页面。即使短暂断开，已开始的操作仍会继续。', ''),
    'handoff': ('先在 HACS 完成一步操作', '发现你以前通过 HACS 安装过 NexHome。请按下方指引停止由它管理这个组件，保留 Home Assistant 中的 NexHome 设备与设置。', '我已经完成，重新检查'),
    'installed': ('友邻加强版已经安装，接下来连接 NexHome 中控', '点击“开始连接 NexHome”，按提示确认自己的中控，再找一盏灯试一次控制。', '开始连接 NexHome'),
    'configured': ('设备已连接，完成第一次操作', '在 Home Assistant 找到一盏方便测试的灯，开关一次，核对实际动作和页面状态，再回来检查。已有配置会继续使用。', '查看 NexHome 设备'),
    'ready': ('安装完成', '已确认设备可以正常控制和同步状态。现在可以在 Home Assistant 中使用。', '查看 NexHome 设备'),
    'restored': ('这次安装没有成功', '已经恢复到安装前的状态。', '重新检查'),
    'recovery': ('自动恢复没有完全完成', '为了避免继续修改你的 Home Assistant，我们已经停止操作。请先查看恢复方法。', '查看恢复方法'),
    'interrupted': ('上一次操作还没有结束', '先检查已保存的进度，再决定是否继续。现在不会重新开始安装。', '检查恢复进度'),
    'unhealthy': ('Home Assistant 还没有准备好', '请等 Home Assistant 恢复正常后重新检查。现在不会开始安装。', '重新检查'),
    'connection_wait': ('原来的 NexHome 连接还没有准备好', '先在 Home Assistant 检查连接。这里不会删除或重新添加你的设备和设置。', '重新检查'),
    'unsupported': ('当前 Home Assistant 版本还未验证', '为了稳妥起见，现在先不安装。可以在详情里查看已验证的版本。', '查看详情'),
    'failed': ('这一步没有完成', '尚未确认完成。请查看原因或重新检查，不要反复点击开始。', '重新检查'),
}

OWNER_SCREEN = {
    None: 'fresh', Owner.OFFICIAL_HACS: 'official', Owner.COMMUNITY_HACS: 'hacs',
    Owner.MANUAL_UNKNOWN: 'unknown', Owner.OWNERSHIP_CONFLICT: 'conflict',
}

PHASE_LABELS = {
    'PRECHECK': '正在检查 Home Assistant', 'PREVIEW': '正在准备安装',
    'BACKUP': '正在备份你现在的 NexHome', 'DEPLOY': '正在安装',
    'ACTIVATE': '正在重新启动 Home Assistant', 'HEALTH_CHECK': '正在检查安装结果',
    'VERIFY_OWNER': '正在确认安装结果', 'COMMITTED': '友邻加强版已安装',
    'FAIL': '安装没有成功，正在检查恢复方法', 'ROLLBACK': '正在恢复安装前的状态',
    'RESTORE': '正在检查恢复结果', 'ROLLED_BACK': '已经恢复到安装前的状态',
    'RECOVERY_REQUIRED': '已停止操作，请查看恢复方法', 'SOURCE_RELEASED': '正在准备安装',
}

HACS_STEPS = [
    '打开 HACS，找到官方 NexHome。',
    '打开右上角菜单，选择 Remove（移除）。如果提示已经配置，选择 IGNORE（保留现有配置并继续）。不要去删除 Home Assistant 中的 NexHome 设置。',
    '确认 REMOVE（移除）后返回这里，点击“我已经完成，重新检查”。我们会先核对，再继续安装。',
]
