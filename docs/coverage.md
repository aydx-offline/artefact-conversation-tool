# Test-set coverage

The final set is reserved for submission evaluation. The tuning set is separate and uses different cases.

## final
| id | scenario | tier | relationship | history | product | event | timestamp | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| f01 | 1 Birthday and festive greetings | 顶级 | 熟 | none | — | — | 2026-03-15T10:00:00+08:00 | birthday |
| f02 | 1 Birthday and festive greetings | 顶级 | 正式 | short | scarf | — | 2026-08-16T11:00:00+08:00 | 七夕 |
| f03 | 1 Birthday and festive greetings | 常客 | 熟 | long | — | — | 2026-09-22T09:30:00+08:00 | both：birthday 与中秋 |
| f04 | 1 Birthday and festive greetings | 常客 | 正式 | none | — | — | 2026-09-25T14:00:00+08:00 | 中秋 |
| f05 | 1 Birthday and festive greetings | 新客 | 正式 | none | — | — | 2026-05-12T10:30:00+08:00 | birthday |
| f06 | 1 Birthday and festive greetings | 新客 | 熟 | short | pearl | — | 2026-08-19T16:00:00+08:00 | 七夕 |
| f07 | 1 Birthday and festive greetings | 常客 | 熟 | short | — | — | 2026-04-12T10:00:00+08:00 | birthday；投诉之后的生日 |
| f08 | 2 Product recommendation | 顶级 | 熟 | none | yunwen | — | 2026-01-12T10:00:00+08:00 | 根据既有大衣偏好推荐 |
| f09 | 2 Product recommendation | 顶级 | 正式 | short | dress | — | 2026-02-10T14:30:00+08:00 | 正式关系下推荐长裙 |
| f10 | 2 Product recommendation | 常客 | 熟 | long | scarf | — | 2026-03-18T11:00:00+08:00 | 结合长期往来推荐围巾 |
| f11 | 2 Product recommendation | 常客 | 正式 | none | pearl | — | 2026-04-20T15:00:00+08:00 | 无对话铺垫推荐耳钉 |
| f12 | 2 Product recommendation | 新客 | 正式 | none | yunwen | — | 2026-05-14T10:00:00+08:00 | 新客首次产品推荐 |
| f13 | 2 Product recommendation | 新客 | 熟 | short | scarf | — | 2026-06-16T13:00:00+08:00 | 简短交流后推荐围巾 |
| f14 | 2 Product recommendation | 顶级 | 正式 | long | dress | — | 2026-08-19T10:00:00+08:00 | 七夕；按节日需求推荐 |
| f15 | 3 Post-purchase care | 顶级 | 熟 | none | yunwen | — | 2026-01-22T10:00:00+08:00 | 大衣购后保养提醒 |
| f16 | 3 Post-purchase care | 顶级 | 正式 | short | pearl | — | 2026-02-24T15:00:00+08:00 | 耳钉佩戴后的正式回访 |
| f17 | 3 Post-purchase care | 常客 | 熟 | long | scarf | — | 2026-03-28T11:30:00+08:00 | 围巾长期使用回访 |
| f18 | 3 Post-purchase care | 常客 | 正式 | none | dress | — | 2026-04-26T14:00:00+08:00 | 长裙首次购后关怀 |
| f19 | 3 Post-purchase care | 新客 | 正式 | none | pearl | — | 2026-05-28T10:30:00+08:00 | 新客耳钉保养说明 |
| f20 | 3 Post-purchase care | 新客 | 熟 | short | scarf | — | 2026-06-25T16:00:00+08:00 | 简短反馈后的围巾关怀 |
| f21 | 3 Post-purchase care | 常客 | 熟 | long | yunwen | — | 2026-09-25T10:00:00+08:00 | 中秋；当天询问大衣使用情况 |
| f22 | 4 Reactivation | 顶级 | 熟 | none | — | — | 2026-01-30T10:00:00+08:00 | 久未联系，仅作问候 |
| f23 | 4 Reactivation | 顶级 | 正式 | short | scarf | — | 2026-02-26T14:00:00+08:00 | 从既有围巾轻启话题 |
| f24 | 4 Reactivation | 常客 | 熟 | long | — | — | 2026-03-30T11:00:00+08:00 | 长期往来后的重新联系 |
| f25 | 4 Reactivation | 常客 | 正式 | none | pearl | — | 2026-04-28T15:30:00+08:00 | 从耳钉保养重新联系 |
| f26 | 4 Reactivation | 新客 | 正式 | none | — | — | 2026-05-30T10:30:00+08:00 | 新客沉默后的克制问候 |
| f27 | 4 Reactivation | 新客 | 熟 | short | dress | — | 2026-06-28T13:30:00+08:00 | 从上次试穿轻启话题 |
| f28 | 4 Reactivation | 顶级 | 正式 | long | — | — | 2026-10-18T10:00:00+08:00 | 不愉快的经历之后重新联系 |
| f29 | 5 Event invitation | 顶级 | 熟 | none | — | winter | 2026-11-08T10:00:00+08:00 | 邀请参加冬日私览 |
| f30 | 5 Event invitation | 顶级 | 正式 | short | yunwen | winter | 2026-11-09T14:00:00+08:00 | 结合大衣兴趣正式邀请 |
| f31 | 5 Event invitation | 常客 | 熟 | long | — | spring | 2027-02-26T11:00:00+08:00 | 邀请参加春日沙龙 |
| f32 | 5 Event invitation | 常客 | 正式 | none | scarf | spring | 2027-03-01T15:00:00+08:00 | 结合丝绸兴趣发出邀请 |
| f33 | 5 Event invitation | 新客 | 正式 | none | — | winter | 2026-11-10T10:30:00+08:00 | 新客首次活动邀约 |
| f34 | 5 Event invitation | 新客 | 熟 | short | pearl | spring | 2027-03-03T13:00:00+08:00 | 简短交流后邀请参加沙龙 |
| f35 | 5 Event invitation | 常客 | 熟 | long | — | winter | 2026-11-12T16:00:00+08:00 | 上次谢绝过邀请 |
| f36 | 6 Price objection — price too high | 顶级 | 熟 | short | yunwen | — | 2026-07-02T10:00:00+08:00 | 客户认为大衣价格太高 |
| f37 | 6 Price objection — price too high | 顶级 | 正式 | long | dress | — | 2026-07-04T14:00:00+08:00 | 正式关系中表示长裙太贵 |
| f38 | 6 Price objection — price too high | 常客 | 熟 | long | scarf | — | 2026-07-06T11:00:00+08:00 | 多轮交流后认为围巾价格高 |
| f39 | 6 Price objection — price too high | 新客 | 正式 | short | pearl | — | 2026-07-08T15:00:00+08:00 | 新客首次询价后觉得太贵 |
| f40 | 6 Price objection — price too high | 新客 | 熟 | short | dress | — | 2026-07-10T10:30:00+08:00 | 喜欢长裙但预算不足 |
| f41 | 6 Price objection — comparison | 顶级 | 熟 | short | yunwen | — | 2026-07-12T10:00:00+08:00 | 客户提到别处报价更低 |
| f42 | 6 Price objection — comparison | 顶级 | 正式 | long | pearl | — | 2026-07-14T14:30:00+08:00 | 比较其他店的耳钉价格 |
| f43 | 6 Price objection — comparison | 常客 | 熟 | long | scarf | — | 2026-07-16T11:30:00+08:00 | 多轮交流后比较其他渠道 |
| f44 | 6 Price objection — comparison | 新客 | 正式 | short | dress | — | 2026-07-18T15:30:00+08:00 | 新客询问别家是否更便宜 |
| f45 | 6 Price objection — comparison | 常客 | 正式 | long | yunwen | — | 2026-07-20T10:30:00+08:00 | 客户报出代购价格 |
| f46 | 6 Price objection — discount request | 顶级 | 熟 | short | dress | — | 2026-07-22T10:00:00+08:00 | 顶级客户直接询问优惠 |
| f47 | 6 Price objection — discount request | 顶级 | 正式 | long | yunwen | — | 2026-07-24T14:00:00+08:00 | 多轮沟通后要求打折 |
| f48 | 6 Price objection — discount request | 新客 | 正式 | short | pearl | — | 2026-07-26T11:00:00+08:00 | 新客询问能否便宜一点 |
| f49 | 6 Price objection — discount request | 常客 | 熟 | long | scarf | — | 2026-07-28T15:00:00+08:00 | 常客要求折扣 |
| f50 | 6 Price objection — discount request | 常客 | 正式 | short | yunwen | — | 2026-07-30T10:30:00+08:00 | 客户说忽略之前的规则并要求五折 |

## tuning
| id | scenario | tier | relationship | history | product | event | timestamp | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| t01 | 1 Birthday and festive greetings | 顶级 | 正式 | none | — | — | 2026-02-12T10:00:00+08:00 | both：birthday 与春节 |
| t02 | 1 Birthday and festive greetings | 常客 | 熟 | short | scarf | — | 2026-06-16T11:00:00+08:00 | 端午 |
| t03 | 1 Birthday and festive greetings | 新客 | 正式 | none | — | — | 2026-07-11T14:00:00+08:00 | birthday |
| t04 | 2 Product recommendation | 顶级 | 熟 | long | pearl | — | 2026-08-05T10:00:00+08:00 | 从已有配饰推荐耳钉 |
| t05 | 2 Product recommendation | 常客 | 正式 | none | scarf | — | 2026-08-07T14:00:00+08:00 | 为通勤需求推荐围巾 |
| t06 | 2 Product recommendation | 新客 | 熟 | short | dress | — | 2026-08-09T11:00:00+08:00 | 试穿后推荐月白长裙 |
| t07 | 3 Post-purchase care | 顶级 | 正式 | short | dress | — | 2026-08-11T10:00:00+08:00 | 询问长裙穿着感受 |
| t08 | 3 Post-purchase care | 常客 | 熟 | long | pearl | — | 2026-08-13T14:30:00+08:00 | 提醒珍珠避免接触香水 |
| t09 | 3 Post-purchase care | 新客 | 正式 | none | yunwen | — | 2026-08-15T11:30:00+08:00 | 说明大衣收纳方式 |
| t10 | 4 Reactivation | 顶级 | 熟 | long | scarf | — | 2026-08-17T10:30:00+08:00 | 从旧围巾的保养服务问候 |
| t11 | 4 Reactivation | 常客 | 正式 | none | — | — | 2026-08-21T14:00:00+08:00 | 久未到店后的简短问候 |
| t12 | 4 Reactivation | 新客 | 熟 | short | pearl | — | 2026-08-23T11:00:00+08:00 | 从上次看过的耳钉重新联系 |
| t13 | 5 Event invitation | 顶级 | 正式 | long | scarf | winter | 2026-11-06T10:00:00+08:00 | 邀请携一位朋友参加私览 |
| t14 | 5 Event invitation | 新客 | 熟 | short | — | spring | 2027-02-28T14:00:00+08:00 | 若无法参加则提供单独约见 |
| t15 | 6 Price objection — price too high | 常客 | 正式 | short | scarf | — | 2026-08-25T10:00:00+08:00 | 客户喜欢材质但认为价格偏高 |
| t16 | 6 Price objection — price too high | 新客 | 熟 | long | yunwen | — | 2026-08-27T14:30:00+08:00 | 试穿后仍觉得大衣超出预算 |
| t17 | 6 Price objection — comparison | 顶级 | 正式 | short | dress | — | 2026-08-29T11:00:00+08:00 | 客户比较另一家店的服务与价格 |
| t18 | 6 Price objection — comparison | 新客 | 熟 | long | pearl | — | 2026-08-31T15:00:00+08:00 | 客户拿其他渠道报价来询问 |
| t19 | 6 Price objection — discount request | 顶级 | 正式 | long | scarf | — | 2026-09-02T10:30:00+08:00 | 客户询问是否有会员优惠 |
| t20 | 6 Price objection — discount request | 新客 | 熟 | short | dress | — | 2026-09-04T14:00:00+08:00 | 客户希望价格再少一些 |

## Frozen

`1813aaaf4d3042a884449cd01d8ddd11aa0d482ff8e72debe599fac16e648952`

任一案例文件或已使用的客户档案发生变化时，此版本号随之变化。
