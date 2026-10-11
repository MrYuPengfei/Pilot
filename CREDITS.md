# 素材授权清单（CREDITS）

本文件记录本项目使用的**第三方素材**及其授权协议。

> ⚠️ **代码协议与素材协议相互独立**：本项目源码协议不代表素材协议。
> 图片 / 音频各自的授权条款独立生效，打包发布必须遵守素材本身的协议。
> 目录约定：`data/CCO/` 放 CC0 素材，`data/CC-BY/` 放需署名的素材。

## 协议分类说明

| 协议 | 是否需要署名 | 能否修改 | 能否打包分发 |
| --- | --- | --- | --- |
| **CC0** | 不需要 | 可以 | 可以 |
| **CC-BY-SA 3.0** | **必须署名作者** | 可以，但**衍生作品须同协议发布** | 可以 |

**本项目不包含、也不得添加**：网络动漫 IP 角色、无授权 Live2D 二创模型、
来源不明的 GIF 截图。这类素材仅可本地私人使用，不得进入开源仓库或安装包。

---

## 一、CC0 素材（`data/CCO/`）

### 1. Kenney — Interface Sounds（音效）

| 项目 | 内容 |
| --- | --- |
| 名称 | Kenney Interface Sounds |
| 作者 | Kenney（kenney.nl） |
| 协议 | **CC0 1.0Universal**（无需署名） |
| 来源 | https://kenney.nl/assets/interface-sounds |
| 镜像 | https://github.com/Calinou/kenney-interface-sounds（内容未改动，仅 Ogg→Wav 转码） |
| 本地路径 | `data/CCO/audio/kenney-interface-sounds/` |
| 内容 | 100 个 WAV：按钮点击、确认/取消、开关、导航等 UI 反馈音 |
| 协议原文 | `data/CCO/audio/kenney-interface-sounds/LICENSE.txt` |

适用场景：桌宠点击、弹窗、打招呼等交互反馈音。

### 2. OpenGameArt（音效与 BGM）

抓取工具：`tools/fetch_oga_cc0.py`（按 CC0 标签严格筛选）。
本地路径 `data/CCO/oga/audio/`，共 46 个素材条目（音效 + 循环 BGM + 环境音）。
每条素材的作者与来源见 `data/CCO/oga/audio/` 内各目录下的 `SOURCE.md`，
汇总清单见「附录 A」。

> 抓取范围为「音效 + 音乐」两类 CC0 条目的第1 页（各 24 条）。
> 后续补充：`python tools/fetch_oga_cc0.py 13,12 <页数> <输出json> --download data/CCO/oga`

### 3. OpenGameArt（像素角色）

同理由 `tools/fetch_oga_cc0.py` 按 CC0 + 关键词
（`pixel pet` / `slime` / `kawaii` / `creature` / `animal spritesheet` 等）抓取，
本地路径 `data/CCO/sprites/pets/`，共 39 个素材条目。
逐条署名见「附录 A」。

---

## 二、CC-BY 素材（`data/CC-BY/`）

### LPC 通用像素角色精灵表（Liberated Pixel Cup）

| 项目 | 内容 |
| --- | --- |
| 名称 | Universal LPC Spritesheet Character Generator |
| 作者 | **数十位社区画师**（逐图署名见下方 `CREDITS.csv`） |
| 协议 | **CC-BY-SA 3.0 / GPL 3.0**（双协议，二选一） |
| 来源 | https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator |
| 原始素材 | https://opengameart.org/content/lpc-collection |
| 协议全文 | https://creativecommons.org/licenses/by-sa/3.0/ |
| 本地路径 | `data/CC-BY/lpc/` |
| 内容 | 217 张PNG：身体 / 头部 / 眼睛 / 发型 / 服装 / 表情等分层件 |
| **署名文件** | `data/CC-BY/lpc/CREDITS.csv`（**必须随包分发**） |

**使用条件（务必遵守）**：

1. **必须署名**。`CREDITS.csv` 逐图记录了作者、协议与原始链接，
   已随素材一同放在 `data/CC-BY/lpc/`，应用内应在「关于/致谢」中可访问。
2. **相同方式共享**。若修改了这些图，衍生作品须以 CC-BY-SA 3.0 或 GPL 3.0 发布。
3. **选取范围**。上游 `spritesheets/` 共 88000+ 张图，而 `CREDITS.csv` 仅登记
   13594 行——**并非每张图都有署名依据**。`tools/pick_lpc_assets.py`
   因此以 `CREDITS.csv` 为准筛选，只取有署名的文件；
   新增素材时务必沿用此规则，否则无法履行署名义务。

**分层合成说明**：LPC 素材是分层件，需按`body → torso → head → hair → eyes` 等顺序
叠加才能形成完整角色。完整示例与动画帧说明见
<https://github.com/ElizaWy/LPC>。

---

## 附录 A：OpenGameArt 素材逐条清单

<!-- OGA_TABLE_START -->
| 本地目录 | 原标题 | 作者 | 协议 | 文件数 | 来源 |
| --- | --- | --- | --- | --- | --- |
| `data/CCO/audio/kenney-interface-sounds` | Kenney Interface Sounds | Kenney（kenney.nl） | **CC0 1.0 Universal**（无需署名） | 101 | https://kenney.nl/assets/interface-sounds |
| `data/CCO/oga/audio/3 Melee sounds` | 3 Melee sounds | Dream2Reality | CC0 | 2 | https://opengameart.org/content/3-melee-sounds |
| `data/CCO/oga/audio/35 wooden cracks_hits_destructions` | 35 wooden cracks/hits/destructions | Pompei2 | CC0 | 1 | https://opengameart.org/content/35-wooden-crackshitsdestructions |
| `data/CCO/oga/audio/37 hits_punches` | 37 hits/punches | supergamez2014 | CC0 | 1 | https://opengameart.org/content/37-hitspunches |
| `data/CCO/oga/audio/4 Chiptunes (Adventure)` | 4 Chiptunes (Adventure) | ericdl | CC0 | 1 | https://opengameart.org/content/4-chiptunes-adventure |
| `data/CCO/oga/audio/5 Chiptunes (Action)` | 5 Chiptunes (Action) | SdiviHall | CC0 | 5 | https://opengameart.org/content/5-chiptunes-action |
| `data/CCO/oga/audio/50 RPG sound effects` | 50 RPG sound effects | LunaVR | CC0 | 1 | https://opengameart.org/content/50-rpg-sound-effects |
| `data/CCO/oga/audio/51 UI sound effects (buttons, switches and clicks)` | 51 UI sound effects (buttons, switches and clicks) | gopherapps | CC0 | 2 | https://opengameart.org/content/51-ui-sound-effects-buttons-switches-and-clicks |
| `data/CCO/oga/audio/512 Sound Effects (8-bit style)` | 512 Sound Effects (8-bit style) | DezrasDragons | CC0 | 2 | https://opengameart.org/content/512-sound-effects-8-bit-style |
| `data/CCO/oga/audio/54 Casino sound effects (cards, dice, chips)` | 54 Casino sound effects (cards, dice, chips) | hc | CC0 | 2 | https://opengameart.org/content/54-casino-sound-effects-cards-dice-chips |
| `data/CCO/oga/audio/63 Digital sound effects (lasers, phasers, space etc.)` | 63 Digital sound effects (lasers, phasers, space etc.) | smoke_th | CC0 | 2 | https://opengameart.org/content/63-digital-sound-effects-lasers-phasers-space-etc |
| `data/CCO/oga/audio/8 wet squish, slurp impacts` | 8 wet squish, slurp impacts | XF3DeX | CC0 | 1 | https://opengameart.org/content/8-wet-squish-slurp-impacts |
| `data/CCO/oga/audio/80 CC0 RPG SFX` | 80 CC0 RPG SFX | NoirPhantom89 | CC0 | 1 | https://opengameart.org/content/80-cc0-rpg-sfx |
| `data/CCO/oga/audio/Another space background track` | Another space background track | StumpyStrust | CC0 | 1 | https://opengameart.org/content/another-space-background-track |
| `data/CCO/oga/audio/Awake! (Megawall-10)` | Awake! (Megawall-10) | Footinthebox | CC0 | 2 | https://opengameart.org/content/awake-megawall-10 |
| `data/CCO/oga/audio/Background space track` | Background space track | qubodup | CC0 | 1 | https://opengameart.org/content/background-space-track |
| `data/CCO/oga/audio/Battle Sound Effects` | Battle Sound Effects | remaxim | CC0 | 2 | https://opengameart.org/content/battle-sound-effects |
| `data/CCO/oga/audio/Battle Theme A` | Battle Theme A | JaidynReiman | CC0 | 2 | https://opengameart.org/content/battle-theme-a |
| `data/CCO/oga/audio/Bossa Nova` | Bossa Nova | looneybits | CC0 | 1 | https://opengameart.org/content/bossa-nova |
| `data/CCO/oga/audio/Cave Theme` | Cave Theme | Clint Bellanger | CC0 | 1 | https://opengameart.org/content/cave-theme |
| `data/CCO/oga/audio/Completion sound` | Completion sound. | manwesulimo2004 | CC0 | 3 | https://opengameart.org/content/completion-sound |
| `data/CCO/oga/audio/Creepy Forest (F)` | Creepy Forest (F) | Anonymous (not verified) | CC0 | 1 | https://opengameart.org/content/creepy-forest-f |
| `data/CCO/oga/audio/Crystal Cave (song18)` | Crystal Cave (song18) | messersm | CC0 | 2 | https://opengameart.org/content/crystal-cave-song18 |
| `data/CCO/oga/audio/Cyberpunk Moonlight Sonata` | Cyberpunk Moonlight Sonata | withthelove | CC0 | 3 | https://opengameart.org/content/cyberpunk-moonlight-sonata |
| `data/CCO/oga/audio/Different steps on wood, stone, leaves, gravel and mud` | Different steps on wood, stone, leaves, gravel and mud | qubodup | CC0 | 2 | https://opengameart.org/content/different-steps-on-wood-stone-leaves-gravel-and-mud |
| `data/CCO/oga/audio/Dripping water loop` | Dripping water loop | supergamez2014 | CC0 | 2 | https://opengameart.org/content/dripping-water-loop |
| `data/CCO/oga/audio/Enchanted Tiki 86` | Enchanted Tiki 86 | Tozan | CC0 | 2 | https://opengameart.org/content/enchanted-tiki-86 |
| `data/CCO/oga/audio/Fast fight _ battle music` | Fast fight / battle music | Bonsaiheldin | CC0 | 2 | https://opengameart.org/content/fast-fight-battle-music |
| `data/CCO/oga/audio/GUI Sound Effects` | GUI Sound Effects | Anonymous (not verified) | CC0 | 1 | https://opengameart.org/content/gui-sound-effects |
| `data/CCO/oga/audio/Level up, power up, Coin get (13 Sounds)` | Level up, power up, Coin get (13 Sounds) | joaquinton | CC0 | 2 | https://opengameart.org/content/level-up-power-up-coin-get-13-sounds |
| `data/CCO/oga/audio/Loading screen loop` | Loading screen loop | qubodup | CC0 | 2 | https://opengameart.org/content/loading-screen-loop |
| `data/CCO/oga/audio/Loopable Dungeon Ambience` | Loopable Dungeon Ambience | IgnasD | CC0 | 1 | https://opengameart.org/content/loopable-dungeon-ambience |
| `data/CCO/oga/audio/Menu Music` | Menu Music | Tempel | CC0 | 1 | https://opengameart.org/content/menu-music |
| `data/CCO/oga/audio/Mysterious Ambience (song21)` | Mysterious Ambience (song21) | Yword | CC0 | 2 | https://opengameart.org/content/mysterious-ambience-song21 |
| `data/CCO/oga/audio/NES Shooter Music (5 tracks, 3 jingles)` | NES Shooter Music (5 tracks, 3 jingles) | Chris_M_The_Gam... | CC0 | 2 | https://opengameart.org/content/nes-shooter-music-5-tracks-3-jingles |
| `data/CCO/oga/audio/Next to You` | Next to You | SdiviHall | CC0 | 1 | https://opengameart.org/content/next-to-you |
| `data/CCO/oga/audio/RPG Sound Pack` | RPG Sound Pack | HaelDB | CC0 | 2 | https://opengameart.org/content/rpg-sound-pack |
| `data/CCO/oga/audio/Snowfall` | Snowfall | Casimir | CC0 | 2 | https://opengameart.org/content/snowfall |
| `data/CCO/oga/audio/Swish - bamboo stick weapon swhoshes` | Swish - bamboo stick weapon swhoshes | Dread Knight | CC0 | 1 | https://opengameart.org/content/swish-bamboo-stick-weapon-swhoshes |
| `data/CCO/oga/audio/Swishes Sound Pack` | Swishes Sound Pack | qubodup | CC0 | 2 | https://opengameart.org/content/swishes-sound-pack |
| `data/CCO/oga/audio/The Field Of Dreams` | The Field Of Dreams | Anonymous (not verified) | CC0 | 1 | https://opengameart.org/content/the-field-of-dreams |
| `data/CCO/oga/audio/Town Theme RPG` | Town Theme RPG | Bonsaiheldin | CC0 | 2 | https://opengameart.org/content/town-theme-rpg |
| `data/CCO/oga/audio/Tragic ambient main menu` | Tragic ambient main menu | Pompei2 | CC0 | 1 | https://opengameart.org/content/tragic-ambient-main-menu |
| `data/CCO/oga/audio/rain and thunders` | rain and thunders | mikhog | CC0 | 1 | https://opengameart.org/content/rain-and-thunders |
| `data/CCO/oga/audio/wind1` | wind1 | qubodup | CC0 | 5 | https://opengameart.org/content/wind1 |
| `data/CCO/oga/mixed/Free Music Pack` | Free Music Pack | FacadeGaikan | CC0 | 2 | https://opengameart.org/content/free-music-pack |
| `data/CCO/oga/mixed/Voiceover Pack (40+ lines)` | Voiceover Pack (40+ lines) | warrior1988 | CC0 | 2 | https://opengameart.org/content/voiceover-pack-40-lines |
| `data/CCO/sprites/pets/A Cat` | A Cat | dannorder | CC0 | 2 | https://opengameart.org/content/a-cat |
| `data/CCO/sprites/pets/A blocky dungeon` | A blocky dungeon | ILIKESCIFI | CC0 | 4 | https://opengameart.org/content/a-blocky-dungeon |
| `data/CCO/sprites/pets/Alien Spaceship Sprite Pack` | Alien Spaceship Sprite Pack | johndh | CC0 | 1 | https://opengameart.org/content/alien-spaceship-sprite-pack |
| `data/CCO/sprites/pets/Animal Pack Redux` | Animal Pack Redux | Snabisch | CC0 | 2 | https://opengameart.org/content/animal-pack-redux |
| `data/CCO/sprites/pets/Bat (32x32)` | Bat (32x32) | Anonymous (not verified) | CC0 | 2 | https://opengameart.org/content/bat-32x32 |
| `data/CCO/sprites/pets/Bevouliin Free Game Sprites - Crocodile Mascot Running and J` | Bevouliin Free Game Sprites - Crocodile Mascot Running and Jumping Boy Game Character | asepafandi89 | CC0 | 1 | https://opengameart.org/content/bevouliin-free-game-sprites-crocodile-mascot-running-and-jumping-boy-game-character |
| `data/CCO/sprites/pets/Blob_Slime collection` | Blob/Slime collection | -Ryu- | CC0 | 2 | https://opengameart.org/content/blobslime-collection |
| `data/CCO/sprites/pets/Casual Game Button Pack` | Casual Game Button Pack | Calinou | CC0 | 1 | https://opengameart.org/content/casual-game-button-pack |
| `data/CCO/sprites/pets/Cat & Dog - Free Sprites` | Cat & Dog - Free Sprites | Pooya | CC0 | 1 | https://opengameart.org/content/cat-dog-free-sprites |
| `data/CCO/sprites/pets/Chick` | Chick | Flixberry Enter... | CC0 | 3 | https://opengameart.org/content/chick |
| `data/CCO/sprites/pets/Concrete UI, part 2` | Concrete UI, part 2 | dalonedrau | CC0 | 2 | https://opengameart.org/content/concrete-ui-part-2 |
| `data/CCO/sprites/pets/Cute cat (32x32)` | Cute cat (32x32) | 未标注 | CC0 | 2 | https://opengameart.org/content/cute-cat-32x32 |
| `data/CCO/sprites/pets/DENZI's public domain art` | DENZI's public domain art | bbulle | CC0 | 5 | https://opengameart.org/content/denzis-public-domain-art |
| `data/CCO/sprites/pets/Dungeon Crawl 32x32 tiles` | Dungeon Crawl 32x32 tiles | bart | CC0 | 8 | https://opengameart.org/content/dungeon-crawl-32x32-tiles |
| `data/CCO/sprites/pets/Dungeon Crawl 32x32 tiles supplemental` | Dungeon Crawl 32x32 tiles supplemental | vlzvl | CC0 | 7 | https://opengameart.org/content/dungeon-crawl-32x32-tiles-supplemental |
| `data/CCO/sprites/pets/Free Game GUI` | Free Game GUI | Aetherna | CC0 | 1 | https://opengameart.org/content/free-game-gui |
| `data/CCO/sprites/pets/Game Button Pack` | Game Button Pack | ErLuiSSJL | CC0 | 1 | https://opengameart.org/content/game-button-pack |
| `data/CCO/sprites/pets/Gothicvania Patreon's Collection` | Gothicvania Patreon's Collection | looneybits | CC0 | 7 | https://opengameart.org/content/gothicvania-patreons-collection |
| `data/CCO/sprites/pets/Kawaii must die` | Kawaii must die | Julius | CC0 | 1 | https://opengameart.org/content/kawaii-must-die |
| `data/CCO/sprites/pets/Limbo Land Monster Sprites` | Limbo Land Monster Sprites | HR78 | CC0 | 1 | https://opengameart.org/content/limbo-land-monster-sprites |
| `data/CCO/sprites/pets/Loveable Rogue` | Loveable Rogue | mfburn | CC0 | 3 | https://opengameart.org/content/loveable-rogue |
| `data/CCO/sprites/pets/Monsterboy in Wonder World mockup assets` | Monsterboy in Wonder World mockup assets | Redshrike | CC0 | 3 | https://opengameart.org/content/monsterboy-in-wonder-world-mockup-assets |
| `data/CCO/sprites/pets/Open Pixel Platformer Tiles & Sprites` | Open Pixel Platformer Tiles & Sprites | Hapiel | CC0 | 6 | https://opengameart.org/content/open-pixel-platformer-tiles-sprites |
| `data/CCO/sprites/pets/Orange Fat Cat` | Orange Fat Cat | cdgramos | CC0 | 2 | https://opengameart.org/content/orange-fat-cat |
| `data/CCO/sprites/pets/Pixel Puncher Sprites` | Pixel Puncher Sprites | Redshrike | CC0 | 7 | https://opengameart.org/content/pixel-puncher-sprites |
| `data/CCO/sprites/pets/Pixel Rabbit People` | Pixel Rabbit People | Demetrius | CC0 | 2 | https://opengameart.org/content/pixel-rabbit-people |
| `data/CCO/sprites/pets/Pixel cat` | Pixel cat | Spring Spring | CC0 | 1 | https://opengameart.org/content/pixel-cat |
| `data/CCO/sprites/pets/Plant Pets` | Plant Pets | AntumDeluge | CC0 | 12 | https://opengameart.org/content/plant-pets |
| `data/CCO/sprites/pets/Radish creature` | Radish creature | 未标注 | CC0 | 4 | https://opengameart.org/content/radish-creature |
| `data/CCO/sprites/pets/Side Blaster GFX (M484 Games)` | Side Blaster GFX (M484 Games) | kheftel | CC0 | 4 | https://opengameart.org/content/side-blaster-gfx-m484-games |
| `data/CCO/sprites/pets/Space War Man_ platform shmup set` | Space War Man: platform shmup set | ZomBCool | CC0 | 34 | https://opengameart.org/content/space-war-man-platform-shmup-set |
| `data/CCO/sprites/pets/The Boy - Free Sprites` | The Boy - Free Sprites | looneybits | CC0 | 1 | https://opengameart.org/content/the-boy-free-sprites |
| `data/CCO/sprites/pets/Tiny Creatures` | Tiny Creatures | food_please | CC0 | 6 | https://opengameart.org/content/tiny-creatures |
| `data/CCO/sprites/pets/Unfinished dungeon tileset` | Unfinished dungeon tileset | pbondoer | CC0 | 2 | https://opengameart.org/content/unfinished-dungeon-tileset |
| `data/CCO/sprites/pets/Various Creatures` | Various Creatures | Boom Shaka | CC0 | 2 | https://opengameart.org/content/various-creatures |
| `data/CCO/sprites/pets/gb funky fauna` | gb funky fauna | 未标注 | CC0 | 2 | https://opengameart.org/content/gb-funky-fauna |
| `data/CCO/sprites/pets/pixel horse` | pixel horse | Spring Spring | CC0 | 6 | https://opengameart.org/content/pixel-horse |
| `data/CCO/sprites/pets/pixel turtle` | pixel turtle | Snabisch | CC0 | 6 | https://opengameart.org/content/pixel-turtle |
| `data/CCO/sprites/pets/shuaagotchi crab virtual pet` | shuaagotchi crab virtual pet | 未标注 | CC0 | 2 | https://opengameart.org/content/shuaagotchi-crab-virtual-pet |

共 86 个素材条目，341 个文件。

> 全部为 **CC0**：无需署名、可修改、可打包分发。
> 每个素材目录内另有 `SOURCE.md` 记录同一信息。
<!-- OGA_TABLE_END -->

---

## 合规检查清单

发布前逐项确认：

- [ ] 安装包内不含任何 CC-BY 素材而未附带 `CREDITS.md` 与素材 `CREDITS.csv`
- [ ] 应用界面内可访问本文件（关于/致谢入口）
- [ ] 未引入动漫 IP 角色、无授权 Live2D 模型、来源不明素材
- [ ] CC-BY-SA 素材的衍生修改仍以相同协议发布
- [ ] 新增素材时同步更新本文件，并放入对应协议目录（`data/CCO/` 或 `data/CC-BY/`）
