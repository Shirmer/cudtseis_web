import { SITE, type Locale } from '../config/site'

export interface LegalSection {
  title: string
  paragraphs?: string[]
  list?: string[]
  items?: { title: string; text: string }[]
}

export interface LegalDoc {
  title: string
  label: string
  intro: string[]
  sections: LegalSection[]
  contact: { title: string; paragraphs: string[]; rows: { label: string; value: string }[] }
}

const companyZh = `${SITE.companyZh}（以下简称"我们"）`
const companyEn = `${SITE.companyEn} ("we", "us" or "our")`

export const privacy: Record<Locale, LegalDoc> = {
  zh: {
    title: '隐私政策',
    label: 'LEGAL / PRIVACY',
    intro: [
      `${companyZh}深知个人信息对您的重要性。本隐私政策适用于 GeoCamera 地质相机移动应用（以下简称"本应用"）及配套的云端服务与管理后台。我们依据《中华人民共和国个人信息保护法》《中华人民共和国网络安全法》《中华人民共和国数据安全法》等法律法规制定本政策，并严格按照本政策处理您的个人信息。`,
      '请您在使用本应用前仔细阅读并充分理解本政策。一旦您开始使用本应用，即表示您已阅读并同意本政策所述的个人信息处理规则。'
    ],
    sections: [
      {
        title: '一、我们收集和使用的信息',
        items: [
          { title: '账号信息', text: '注册与登录时提供的邮箱地址、昵称及加密后的登录凭据，用于账号创建、身份验证与服务同步。' },
          { title: '位置信息', text: '包括精确位置与粗略位置。在您拍摄照片、记录路线时用于为影像与轨迹写入坐标；开启后台定位时，用于在息屏或应用退到后台时持续记录野外路线。' },
          { title: '影像与元数据', text: '您通过相机拍摄或从相册导入的照片/视频，以及附带的坐标、海拔、方位等记录信息。' },
          { title: '设备与日志信息', text: '设备型号、操作系统版本、应用版本号、崩溃与运行日志，用于故障诊断、安全防护与服务优化。' },
          { title: '您主动提供的信息', text: '项目名称、路线描述、反馈意见等您在使用过程中主动填写的内容。' }
        ]
      },
      {
        title: '二、设备权限说明',
        paragraphs: [
          '为实现核心功能，本应用可能向您申请以下设备权限，均在您授权后启用。您可以随时在系统设置中关闭授权，但可能导致部分功能不可用：'
        ],
        list: [
          '相机：拍摄地质影像与视频，用于露头、剖面与构造现象的记录；',
          '位置（前台与后台）：为照片写入坐标，记录野外路线轨迹；仅在您主动开启路线记录时使用后台定位；',
          '存储：保存、读取与管理应用拍摄的照片与报告文件；',
          '通知：同步状态、任务进度等消息提醒；',
          '蓝牙：连接可用的外部设备（如您使用相关功能）；',
          '麦克风：录制语音备注（如您使用该功能）；',
          '安装未知应用：应用内版本更新与升级。'
        ]
      },
      {
        title: '三、信息的使用',
        list: [
          '提供核心功能：照片定位、路线记录、云端同步与路线报告导出；',
          '账号与安全管理：登录验证、数据权限控制与安全风控；',
          '服务优化：故障排查、性能分析与体验改进；',
          '与您沟通：回应您的咨询、反馈与技术支持请求。'
        ]
      },
      {
        title: '四、信息的存储',
        paragraphs: [
          '我们在中华人民共和国境内收集和产生的个人信息，存储于境内的服务器与云存储中，不会向境外传输。位置、影像等数据通过网络加密传输，云端数据存储于我们采用的合规云服务中。',
          '我们仅在实现本政策所述目的所必需的期限内保存您的个人信息，法律法规另有规定的除外。您注销账号后，我们将删除或匿名化处理您的个人信息。'
        ]
      },
      {
        title: '五、信息的共享、转让与公开披露',
        list: [
          '我们不会出售您的个人信息；',
          '未经您的同意，我们不会向第三方共享、转让您的个人信息，法律法规另有规定的除外；',
          '在涉及合并、分立、解散或破产等情形需要转移个人信息时，我们会告知您接收方的名称与联系方式，并要求接收方继续履行本政策义务；',
          '我们不会公开披露您的个人信息，法律法规要求或获得您单独同意的情形除外。'
        ]
      },
      {
        title: '六、第三方服务',
        paragraphs: [
          '为实现地图底图展示、云存储等功能，本应用可能接入第三方服务。我们会对第三方服务进行安全评估，并尽合理努力要求其按照法律法规与相应协议处理相关信息。'
        ]
      },
      {
        title: '七、信息安全',
        paragraphs: [
          '我们采用符合行业标准的安全措施（如传输加密、访问控制、权限隔离等）保护您的个人信息，防止未经授权的访问、披露、使用、修改、损坏或丢失。',
          '尽管我们已采取合理措施，但请理解互联网环境并非绝对安全。如发生个人信息安全事件，我们将按照法律法规要求及时告知您并上报监管部门。'
        ]
      },
      {
        title: '八、您的权利',
        list: [
          '访问与更正：您可以在应用内查看并更正您的账号信息；',
          '删除：您可以删除应用内的照片、路线与项目数据；',
          '撤回同意：您可以在系统设置中关闭相关权限；',
          '注销账号：您可以通过本政策载明的联系方式申请注销账号；',
          '投诉与举报：如您认为我们处理个人信息的行为损害了您的合法权益，可通过本政策联系方式与我们联系，或向监管部门投诉、举报。'
        ]
      },
      {
        title: '九、未成年人保护',
        paragraphs: [
          '本应用主要面向专业从业人员，我们不主动收集未成年人的个人信息。如您为未成年人，请在监护人陪同下阅读本政策，并在取得监护人同意后使用本应用。'
        ]
      },
      {
        title: '十、本政策的更新',
        paragraphs: [
          '我们可能适时更新本政策。更新后的政策将在本页面公布，涉及重大变更时我们将以显著方式通知您。若您在政策更新后继续使用本应用，即表示您接受更新后的政策。'
        ]
      }
    ],
    contact: {
      title: '十一、联系我们',
      paragraphs: ['如您对本政策或个人信息保护有任何疑问、意见或建议，可通过以下方式联系我们，我们将尽快回复：'],
      rows: [
        { label: '公司名称', value: SITE.companyZh },
        { label: '电子邮箱', value: SITE.contact.email }
      ]
    }
  },
  en: {
    title: 'Privacy Policy',
    label: 'LEGAL / PRIVACY',
    intro: [
      `${companyEn} understands the importance of personal information. This Privacy Policy applies to the GeoCamera mobile application (the "App") and its related cloud services and admin console. We process your personal information in accordance with this Policy and applicable laws and regulations.`,
      'Please read and fully understand this Policy before using the App. By using the App, you acknowledge that you have read and agree to the information processing rules described in this Policy.'
    ],
    sections: [
      {
        title: '1. Information We Collect and Use',
        items: [
          { title: 'Account information', text: 'Email address, nickname and encrypted credentials provided at registration and login, used for account creation, authentication and service synchronization.' },
          { title: 'Location information', text: 'Precise and coarse location, used to tag coordinates to photos and tracks when you capture images or record routes; background location is used only while route recording is active to keep recording when the screen is off.' },
          { title: 'Images and metadata', text: 'Photos and videos captured with the camera or imported from your gallery, along with associated coordinates, elevation and orientation.' },
          { title: 'Device and log information', text: 'Device model, OS version, app version, crash and runtime logs, used for diagnostics, security protection and service improvement.' },
          { title: 'Information you provide', text: 'Project names, route descriptions, feedback and other content you actively submit.' }
        ]
      },
      {
        title: '2. Device Permissions',
        paragraphs: [
          'The App may request the following permissions to provide core features. All permissions are enabled only after your authorization and can be revoked at any time in system settings, which may disable some features:'
        ],
        list: [
          'Camera: capture geological photos and videos of outcrops, sections and structures;',
          'Location (foreground and background): tag coordinates to photos and record field routes; background location is used only while you actively record a route;',
          'Storage: save, read and manage photos and report files;',
          'Notifications: sync status and task progress reminders;',
          'Bluetooth: connect to compatible external devices (if you use such features);',
          'Microphone: record voice notes (if you use this feature);',
          'Install unknown apps: in-app version updates.'
        ]
      },
      {
        title: '3. How We Use Information',
        list: [
          'Providing core features: photo geotagging, route recording, cloud sync and route report export;',
          'Account and security management: authentication, access control and risk prevention;',
          'Service improvement: troubleshooting, performance analysis and experience optimization;',
          'Communication: responding to your inquiries, feedback and support requests.'
        ]
      },
      {
        title: '4. Storage of Information',
        paragraphs: [
          'Personal information collected and generated within the territory of the People\'s Republic of China is stored on servers and cloud storage located within the territory and will not be transferred abroad. Location, image and other data are transmitted with encryption and stored in compliant cloud services we adopt.',
          'We retain your personal information only for the period necessary to fulfill the purposes described in this Policy, unless otherwise required by law. After you delete your account, we will delete or anonymize your personal information.'
        ]
      },
      {
        title: '5. Sharing, Transfer and Public Disclosure',
        list: [
          'We do not sell your personal information;',
          'We do not share or transfer your personal information to third parties without your consent, except as required by law;',
          'In the event of a merger, division, dissolution or bankruptcy requiring transfer of personal information, we will inform you of the recipient and require it to continue to comply with this Policy;',
          'We do not publicly disclose your personal information except as required by law or with your separate consent.'
        ]
      },
      {
        title: '6. Third-Party Services',
        paragraphs: [
          'The App may integrate third-party services for basemap display and cloud storage. We assess these services for security and make reasonable efforts to require them to process information in accordance with applicable laws and their agreements.'
        ]
      },
      {
        title: '7. Information Security',
        paragraphs: [
          'We adopt industry-standard safeguards (such as encrypted transmission, access control and permission isolation) to protect your personal information against unauthorized access, disclosure, use, modification, damage or loss.',
          'Although we take reasonable measures, please understand that the internet is not absolutely secure. If a personal information security incident occurs, we will notify you and report to regulators in accordance with applicable laws.'
        ]
      },
      {
        title: '8. Your Rights',
        list: [
          'Access and correction: view and correct your account information in the App;',
          'Deletion: delete photos, routes and project data in the App;',
          'Withdrawal of consent: disable permissions in system settings;',
          'Account cancellation: request cancellation via the contact details in this Policy;',
          'Complaints: contact us or file complaints with regulators if you believe your rights have been infringed.'
        ]
      },
      {
        title: '9. Minors',
        paragraphs: [
          'The App is intended for professional users and we do not knowingly collect personal information from minors. If you are a minor, please read this Policy with your guardian and use the App only with your guardian\'s consent.'
        ]
      },
      {
        title: '10. Updates to This Policy',
        paragraphs: [
          'We may update this Policy from time to time. Updates will be published on this page, and material changes will be notified prominently. Continued use of the App after an update constitutes acceptance of the updated Policy.'
        ]
      }
    ],
    contact: {
      title: '11. Contact Us',
      paragraphs: ['If you have any questions, comments or suggestions about this Policy or personal information protection, please contact us:'],
      rows: [
        { label: 'Company', value: SITE.companyEn },
        { label: 'Email', value: SITE.contact.email }
      ]
    }
  }
}

export const terms: Record<Locale, LegalDoc> = {
  zh: {
    title: '用户协议',
    label: 'LEGAL / TERMS',
    intro: [
      '本用户协议是您与深视地球（成都）信息技术有限公司（以下简称"我们"）之间就 GeoCamera 地质相机移动应用及配套服务（以下简称"本服务"）所订立的协议。',
      '请您在注册、登录或使用本服务前，仔细阅读并充分理解本协议全部条款，特别是与免除或限制责任相关的条款。您完成注册或以其他方式使用本服务，即视为您已阅读并同意本协议。'
    ],
    sections: [
      {
        title: '一、协议的范围',
        paragraphs: [
          '本协议适用于 GeoCamera 移动应用、云端服务及相关管理后台（包括后续可能推出的新版本、新功能）。本服务可能包含第三方提供的服务或链接，该部分适用相应的第三方条款。'
        ]
      },
      {
        title: '二、服务内容',
        list: [
          '野外影像采集：拍照、录像，并自动记录位置、海拔与方位信息；',
          '项目与路线管理：按项目组织野外路线，支持离线记录与自动同步；',
          '专业地图：提供地图底图展示，可叠加断层等地质构造数据；',
          '数据同步与管理：将数据同步至云端，并提供团队管理后台；',
          '报告导出：将路线照片与轨迹整理导出为报告文件；',
          '版本更新：通过应用内更新提供新版本与功能改进。'
        ]
      },
      {
        title: '三、账号注册与安全',
        list: [
          '您需提供真实、准确、完整的注册信息，并及时更新；',
          '账号仅供您本人或您所属团队使用，您应妥善保管账号与登录凭据；',
          '因您保管不善导致的账号泄露、数据丢失等后果由您自行承担；',
          '如发现任何未经授权使用您账号的情形，请立即通知我们。'
        ]
      },
      {
        title: '四、用户行为规范',
        paragraphs: ['您在使用本服务时，应遵守法律法规及野外作业相关规定，并不得从事以下行为：'],
        list: [
          '上传、发布法律法规禁止的内容；',
          '未经授权采集、使用涉及国家秘密、商业秘密或个人隐私的信息；',
          '以任何方式干扰、破坏本服务的正常运行，或非法获取、篡改他人数据；',
          '利用本服务从事任何违法违规活动。'
        ]
      },
      {
        title: '五、用户内容与数据',
        paragraphs: [
          '您通过本服务拍摄、上传、存储的照片、轨迹及其他数据（以下简称"用户数据"）归您或相关权利人所有。您授予我们在为您提供服务所必需的范围内使用、存储、传输和处理用户数据的权利。',
          '您应对用户数据的合法性、真实性负责。我们建议您对重要数据自行做好备份。'
        ]
      },
      {
        title: '六、知识产权',
        paragraphs: [
          '本服务的软件、界面设计、文档、商标及其他内容的知识产权归我们或相关权利人所有。未经书面许可，您不得复制、修改、分发、许可或反向工程上述内容。'
        ]
      },
      {
        title: '七、服务变更、中断与终止',
        list: [
          '我们可能根据业务需要变更、暂停或终止部分或全部服务，并尽可能提前通知；',
          '如您违反本协议或法律法规，我们有权暂停或终止向您提供服务；',
          '服务终止后，我们将依照法律法规和《隐私政策》处理您的数据。'
        ]
      },
      {
        title: '八、免责声明',
        paragraphs: [
          '本服务按"现状"提供。在法律允许的最大范围内，我们不对服务的绝对无中断、无差错作出保证。',
          '因不可抗力、网络故障、设备故障、您操作不当等非我们原因造成的服务中断或数据损失，我们在法律允许范围内不承担责任。本服务中的地图、地质数据仅供参考，不构成任何专业结论或决策依据，野外作业请以现场实际情况与专业判断为准。'
        ]
      },
      {
        title: '九、法律适用与争议解决',
        paragraphs: [
          '本协议的订立、效力、解释、履行及争议解决均适用中华人民共和国法律。因本协议产生的争议，双方应友好协商解决；协商不成的，任何一方可向有管辖权的人民法院提起诉讼。'
        ]
      },
      {
        title: '十、协议的更新',
        paragraphs: [
          '我们可能适时修订本协议，修订后的协议将在本页面公布。若您在协议更新后继续使用本服务，即视为您接受修订后的协议。'
        ]
      }
    ],
    contact: {
      title: '十一、联系方式',
      paragraphs: ['如您对本协议有任何疑问，可通过以下方式联系我们：'],
      rows: [
        { label: '公司名称', value: SITE.companyZh },
        { label: '电子邮箱', value: SITE.contact.email }
      ]
    }
  },
  en: {
    title: 'Terms of Service',
    label: 'LEGAL / TERMS',
    intro: [
      `These Terms of Service constitute an agreement between you and ${SITE.companyEn} ("we", "us" or "our") regarding the GeoCamera mobile application and related services (the "Service").`,
      'Please read and fully understand these Terms, especially those concerning exclusions or limitations of liability, before registering, logging in or using the Service. By registering or otherwise using the Service, you acknowledge that you have read and agree to these Terms.'
    ],
    sections: [
      {
        title: '1. Scope',
        paragraphs: [
          'These Terms apply to the GeoCamera mobile application, cloud services and related admin console, including future versions and features. The Service may include third-party services or links, which are governed by the corresponding third-party terms.'
        ]
      },
      {
        title: '2. Service Description',
        list: [
          'Field capture: photograph and record with automatic positioning, elevation and orientation data;',
          'Projects and routes: organize field routes by project with offline recording and automatic synchronization;',
          'Professional maps: basemap display with optional geological structure overlays such as faults;',
          'Data sync and management: cloud synchronization with a team admin console;',
          'Report export: export route photos and tracks as report files;',
          'Updates: in-app version updates and feature improvements.'
        ]
      },
      {
        title: '3. Account Registration and Security',
        list: [
          'You shall provide true, accurate and complete registration information and keep it updated;',
          'Accounts are for you or your team; you are responsible for safeguarding your account credentials;',
          'You bear the consequences of account leakage or data loss caused by your failure to safeguard credentials;',
          'Please notify us immediately of any unauthorized use of your account.'
        ]
      },
      {
        title: '4. Acceptable Use',
        paragraphs: ['You shall comply with applicable laws and field work regulations, and shall not:'],
        list: [
          'upload or publish content prohibited by law;',
          'collect or use information involving state secrets, trade secrets or personal privacy without authorization;',
          'interfere with or disrupt the Service, or illegally obtain or tamper with others\' data;',
          'use the Service for any illegal or non-compliant activity.'
        ]
      },
      {
        title: '5. User Content and Data',
        paragraphs: [
          'Photos, tracks and other data you capture, upload or store through the Service ("User Data") belong to you or the relevant rights holders. You grant us the right to use, store, transmit and process User Data to the extent necessary to provide the Service.',
          'You are responsible for the legality and authenticity of User Data. We recommend keeping your own backups of important data.'
        ]
      },
      {
        title: '6. Intellectual Property',
        paragraphs: [
          'Intellectual property rights in the software, interface design, documentation, trademarks and other content of the Service belong to us or the relevant rights holders. You may not copy, modify, distribute, license or reverse engineer such content without written permission.'
        ]
      },
      {
        title: '7. Changes, Interruption and Termination',
        list: [
          'We may change, suspend or terminate part or all of the Service as needed, with advance notice where possible;',
          'If you violate these Terms or applicable laws, we may suspend or terminate your access to the Service;',
          'After termination, we will handle your data in accordance with applicable laws and the Privacy Policy.'
        ]
      },
      {
        title: '8. Disclaimer',
        paragraphs: [
          'The Service is provided on an "as is" basis. To the maximum extent permitted by law, we do not guarantee uninterrupted or error-free operation.',
          'To the extent permitted by law, we are not liable for service interruption or data loss caused by force majeure, network or device failures, or improper operation. Maps and geological data in the Service are for reference only and do not constitute professional conclusions or decision-making bases; field work shall rely on actual site conditions and professional judgment.'
        ]
      },
      {
        title: '9. Governing Law and Dispute Resolution',
        paragraphs: [
          'These Terms are governed by the laws of the People\'s Republic of China. Disputes arising from these Terms shall be resolved through friendly negotiation; if negotiation fails, either party may bring an action before a competent court.'
        ]
      },
      {
        title: '10. Updates to These Terms',
        paragraphs: [
          'We may revise these Terms from time to time, and the revised version will be published on this page. Continued use of the Service after an update constitutes acceptance of the revised Terms.'
        ]
      }
    ],
    contact: {
      title: '11. Contact',
      paragraphs: ['If you have any questions about these Terms, please contact us:'],
      rows: [
        { label: 'Company', value: SITE.companyEn },
        { label: 'Email', value: SITE.contact.email }
      ]
    }
  }
}
