<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, bootstrap, fileUrl, type Flow, type Run, type Values, type Parameter } from './api'

const page = ref('library')
const flows = ref<Flow[]>([])
const history = ref<Run[]>([])
const selected = ref<Flow | null>(null)
const values = ref<Values>({})
const run = ref<Run | null>(null)
const search = ref('')
const notice = ref('')
const error = ref('')
const busy = ref(false)
const connected = ref(false)
const version = ref('0.2.0')
const dataDir = ref('')
const showImport = ref(false)
const importFile = ref<File | null>(null)
const replace = ref(false)
const trusted = ref(false)
let timer: ReturnType<typeof setInterval> | undefined
let refreshing = false
const filtered = computed(() =>
  flows.value.filter((f) =>
    `${f.name} ${f.description}`.toLowerCase().includes(search.value.toLowerCase()),
  ),
)
const active = computed(() =>
  history.value.find((r) => ['running', 'cancelling'].includes(r.status)),
)
const succeeded = computed(() => history.value.filter((r) => r.status === 'succeeded').length)
const statusNames: Record<string, string> = {
  running: '运行中',
  cancelling: '正在取消',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}
const capabilityNames: Record<string, string> = {
  'file-read': '读取文件',
  'file-write': '生成文件',
  network: '网络访问',
  browser: '浏览器操作',
  'external-write': '外部系统写入',
}
const title = computed(
  () =>
    ({ library: '流程工作台', history: '运行记录', run: '运行详情', guide: '制作流程' })[
      page.value
    ],
)
const formatDate = (text: string) => new Date(text).toLocaleString('zh-CN', { hour12: false })

async function action(work: () => Promise<void>) {
  if (busy.value) return
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    await work()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
async function refresh() {
  if (refreshing) return
  refreshing = true
  try {
    history.value = await api<Run[]>('/runs')
    if (run.value) run.value = await api<Run>(`/runs/${run.value.id}`)
    connected.value = true
  } catch {
    connected.value = false
  } finally {
    refreshing = false
  }
}
async function loadFlows() {
  flows.value = await api<Flow[]>('/flows')
}
async function selectFlow(flow: Flow) {
  await action(async () => {
    const config = await api<Values>(`/flows/${flow.id}/config`)
    values.value = Object.fromEntries(
      flow.parameters.map((p) => [
        p.key,
        config[p.key] ?? p.default ?? (p.type === 'boolean' ? false : ''),
      ]),
    )
    selected.value = flow
  })
}
function cleanValues(): Values {
  return Object.fromEntries(Object.entries(values.value).filter(([, value]) => value !== ''))
}
async function start(dryRun: boolean) {
  await action(async () => {
    if (!selected.value) return
    run.value = await api<Run>('/runs', 'POST', {
      flow_id: selected.value.id,
      config: cleanValues(),
      dry_run: dryRun,
    })
    selected.value.parameters
      .filter((p) => p.secret)
      .forEach((p) => {
        values.value[p.key] = ''
      })
    page.value = 'run'
    await refresh()
  })
}
async function openRun(item: Run) {
  await action(async () => {
    run.value = await api<Run>(`/runs/${item.id}`)
    page.value = 'run'
  })
}
async function cancel() {
  await action(async () => {
    if (run.value) run.value = await api<Run>(`/runs/${run.value.id}/cancel`, 'POST', {})
    await refresh()
  })
}
async function save() {
  await action(async () => {
    if (!selected.value) return
    await api(`/flows/${selected.value.id}/config`, 'PUT', cleanValues())
    notice.value = '配置已保存；敏感字段不会保存。'
  })
}
async function importPackage() {
  await action(async () => {
    if (!importFile.value || !trusted.value) return
    const form = new FormData()
    form.append('file', importFile.value)
    form.append('replace', String(replace.value))
    const flow = await api<Flow>('/flows/import', 'POST', form)
    await loadFlows()
    showImport.value = false
    selected.value = null
    notice.value = `已导入 ${flow.name} · v${flow.version}`
    page.value = 'library'
    importFile.value = null
    trusted.value = false
  })
}
async function installExamples() {
  await action(async () => {
    await api('/examples', 'POST', {})
    await loadFlows()
    notice.value = '两个公开示例已准备好，选择一个开始体验。'
  })
}
async function removeFlow() {
  if (!selected.value || !window.confirm(`卸载「${selected.value.name}」？运行记录和结果会保留。`))
    return
  await action(async () => {
    await api(`/flows/${selected.value!.id}`, 'DELETE')
    selected.value = null
    await loadFlows()
    notice.value = '流程已卸载，历史结果已保留。'
  })
}
function chosenFile(event: Event) {
  return (event.target as HTMLInputElement).files?.[0]
}
async function inputFile(parameter: Parameter, event: Event) {
  const file = chosenFile(event)
  if (!file) return
  await action(async () => {
    const body = new FormData()
    body.append('file', file)
    const result = await api<{ path: string }>('/inputs', 'POST', body)
    values.value[parameter.key] = result.path
  })
}
async function pickDirectory(parameter: Parameter) {
  await action(async () => {
    const result = await api<{ path: string | null }>('/pick-directory', 'POST', {})
    if (result.path) values.value[parameter.key] = result.path
  })
}
onMounted(async () => {
  await action(async () => {
    const info = await bootstrap()
    version.value = info.version
    dataDir.value = info.data_dir
    await loadFlows()
    await refresh()
  })
  timer = setInterval(refresh, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="page = 'library'"
        ><span class="brand-icon">a<span>↗</span></span>
        <div>AutoMatic<span>Worker</span></div></a
      >
      <div class="nav-caption">WORKSPACE</div>
      <nav aria-label="主导航">
        <button :class="{ chosen: page === 'library' }" @click="page = 'library'">
          <span>▦</span> 流程工作台 <small>{{ flows.length }}</small>
        </button>
        <button :class="{ chosen: page === 'history' || page === 'run' }" @click="page = 'history'">
          <span>◷</span> 运行记录 <i v-if="active" class="dot" />
        </button>
        <button :class="{ chosen: page === 'guide' }" @click="page = 'guide'">
          <span>⌘</span> 制作流程
        </button>
      </nav>
      <div class="sidebar-note">
        <span class="spark">✧</span><strong>把重复的工作，交给流程。</strong>
        <p>一个工作台，运行你的自动化工具。</p>
        <button @click="page = 'guide'">了解 AI 制作流程 <span>↗</span></button>
      </div>
      <div class="connection">
        <i class="dot" :class="{ offline: !connected }" />{{
          connected ? '本地服务已连接' : '连接中断，请检查服务'
        }}<small>v{{ version }} · 本地工作空间</small>
      </div>
    </aside>

    <main>
      <header class="topbar">
        <div>
          工作空间 <span>/</span> <strong>{{ title }}</strong>
        </div>
        <span class="local-badge">◉ 本地运行</span>
      </header>
      <div class="content">
        <div v-if="error" class="alert error" role="alert">
          {{ error }}<button aria-label="关闭错误" @click="error = ''">×</button>
        </div>
        <div v-if="notice" class="alert success" role="status">
          {{ notice }}<button aria-label="关闭提示" @click="notice = ''">×</button>
        </div>
        <div v-if="!connected" class="alert error">
          服务暂不可用，任务状态可能不是最新。连接恢复后会自动更新。
        </div>

        <template v-if="page === 'library'">
          <div class="page-heading">
            <div>
              <p class="eyebrow">YOUR AUTOMATION, SIMPLIFIED</p>
              <h1>让工作，自动向前。</h1>
              <p>选择一个流程，配置参数，剩下的交给 AutoMaticWorker。</p>
            </div>
            <button class="primary" :disabled="busy || !!active" @click="showImport = true">
              ＋ 导入流程包
            </button>
          </div>
          <div class="stats">
            <div>
              <span>已安装流程</span
              ><strong>{{ String(flows.length).padStart(2, '0') }}<small>个可用工具</small></strong>
            </div>
            <div>
              <span>已完成运行</span
              ><strong>{{ String(succeeded).padStart(2, '0') }}<small>次成功执行</small></strong>
            </div>
            <div>
              <span>当前任务</span
              ><strong class="status-text"
                >{{ active ? '运行中' : '已就绪'
                }}<small>{{ active ? active.name : '随时开始下一项工作' }}</small></strong
              >
            </div>
          </div>
          <div v-if="active" class="active-banner">
            <i class="dot" /><span>{{ active.name }} · {{ statusNames[active.status] }}</span
            ><button @click="openRun(active)">查看进度 →</button>
          </div>
          <div class="section-heading">
            <div>
              <h2>
                我的流程 <span>{{ flows.length }}</span>
              </h2>
              <p>为每一项重复工作，找到它的自动化方式。</p>
            </div>
            <input v-model="search" class="search" placeholder="搜索流程…" aria-label="搜索流程" />
          </div>
          <div class="workspace-grid" :class="{ 'has-selection': selected }">
            <div>
              <div v-if="!flows.length" class="empty">
                <span class="empty-icon">▦</span>
                <h3>从第一个流程开始</h3>
                <p>导入 ZIP 流程包，或用公开示例体验一次完整运行。</p>
                <button class="primary" :disabled="busy" @click="installExamples">
                  添加体验流程</button
                ><small>合成数据与本地模拟网页，无需账号。</small>
              </div>
              <div v-else-if="!filtered.length" class="empty">
                <h3>没有匹配的流程</h3>
                <button @click="search = ''">清除搜索</button>
              </div>
              <div v-else class="flow-grid">
                <button
                  v-for="flow in filtered"
                  :key="flow.id"
                  class="flow-card"
                  :class="{ selected: selected?.id === flow.id }"
                  :disabled="busy"
                  @click="selectFlow(flow)"
                >
                  <div class="card-top">
                    <span class="flow-icon">{{ flow.id.includes('web') ? '◎' : '▤' }}</span
                    ><span class="version">v{{ flow.version }}</span>
                  </div>
                  <h3>{{ flow.name }}</h3>
                  <p>{{ flow.description }}</p>
                  <div class="tags">
                    <span v-for="cap in flow.capabilities" :key="cap">{{
                      capabilityNames[cap] || cap
                    }}</span>
                  </div>
                  <div class="card-bottom">
                    <span>{{ flow.author }}</span
                    ><strong>配置流程 ↗</strong>
                  </div>
                </button>
              </div>
              <button
                v-if="flows.length"
                class="text-button"
                :disabled="busy || !!active"
                @click="installExamples"
              >
                ＋ 添加公开体验流程
              </button>
            </div>
            <section v-if="selected" class="config-panel" aria-label="流程配置">
              <div class="panel-heading">
                <div>
                  <p class="eyebrow">CONFIGURATION</p>
                  <h2>{{ selected.name }}</h2>
                </div>
                <button class="icon-button" aria-label="关闭配置" @click="selected = null">
                  ×
                </button>
              </div>
              <form @submit.prevent="start(false)">
                <div v-for="p in selected.parameters" :key="p.key" class="field">
                  <label :for="`param-${p.key}`"
                    >{{ p.label }} <span v-if="p.required" class="required">*</span
                    ><small v-if="p.secret">仅本次使用</small></label
                  >
                  <select
                    v-if="p.type === 'enum'"
                    :id="`param-${p.key}`"
                    v-model="values[p.key]"
                    :required="p.required"
                  >
                    <option v-if="!p.required" value="">未选择</option>
                    <option v-for="option in p.options" :key="option" :value="option">
                      {{ option }}
                    </option>
                  </select>
                  <input
                    v-else-if="p.type === 'boolean'"
                    :id="`param-${p.key}`"
                    v-model="values[p.key]"
                    type="checkbox"
                    class="toggle"
                  />
                  <input
                    v-else-if="p.type === 'number'"
                    :id="`param-${p.key}`"
                    v-model.number="values[p.key]"
                    type="number"
                    step="any"
                    :min="p.minimum"
                    :max="p.maximum"
                    :required="p.required"
                  />
                  <template v-else
                    ><input
                      :id="`param-${p.key}`"
                      v-model="values[p.key]"
                      :type="p.secret ? 'password' : 'text'"
                      :required="p.required"
                      :autocomplete="p.secret ? 'new-password' : 'off'"
                    /><label v-if="p.type === 'file'" class="file-button"
                      >选择文件<input type="file" @change="inputFile(p, $event)" /></label
                    ><button
                      v-if="p.type === 'directory'"
                      type="button"
                      class="text-button"
                      @click="pickDirectory(p)"
                    >
                      选择目录
                    </button></template
                  >
                  <p v-if="p.description" class="help">{{ p.description }}</p>
                </div>
                <div class="mode-note">
                  {{
                    selected.dry_run === 'unsupported'
                      ? '此流程不支持试运行。'
                      : selected.dry_run === 'simulation'
                        ? '试运行使用模拟模式，可能生成本地结果文件。'
                        : '试运行预览拟执行的操作。'
                  }}
                </div>
                <div class="form-actions">
                  <button
                    type="button"
                    :disabled="busy || !!active || selected.dry_run === 'unsupported'"
                    @click="start(true)"
                  >
                    试运行</button
                  ><button type="submit" class="primary" :disabled="busy || !!active || !connected">
                    ▶ 开始运行
                  </button>
                </div>
                <div class="panel-footer">
                  <button type="button" class="text-button" :disabled="busy" @click="save">
                    保存配置</button
                  ><button
                    type="button"
                    class="text-button danger"
                    :disabled="busy || !!active"
                    @click="removeFlow"
                  >
                    卸载流程
                  </button>
                </div>
              </form>
            </section>
          </div>
        </template>

        <template v-else-if="page === 'history'">
          <div class="page-heading">
            <div>
              <p class="eyebrow">ACTIVITY</p>
              <h1>每一步，都有迹可循。</h1>
              <p>查看执行记录、排查问题，找到已经完成的结果。</p>
            </div>
          </div>
          <div v-if="!history.length" class="empty">
            <h3>还没有运行记录</h3>
            <p>从工作台运行第一个流程，记录会保存在这里。</p>
            <button @click="page = 'library'">前往工作台 →</button>
          </div>
          <div v-else class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>流程</th>
                  <th>模式</th>
                  <th>状态</th>
                  <th>开始时间</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in history" :key="item.id">
                  <td>
                    <strong>{{ item.name }}</strong
                    ><small>v{{ item.version }}</small>
                  </td>
                  <td>{{ item.dry_run ? '试运行' : '正式运行' }}</td>
                  <td>
                    <span class="status" :class="item.status">{{ statusNames[item.status] }}</span>
                  </td>
                  <td>{{ formatDate(item.started_at) }}</td>
                  <td><button class="text-button" @click="openRun(item)">查看详情 →</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="page === 'run' && run">
          <button class="text-button back" @click="page = 'history'">← 全部运行记录</button>
          <div class="page-heading">
            <div>
              <p class="eyebrow">{{ run.dry_run ? 'SIMULATION' : 'WORKFLOW RUN' }}</p>
              <h1>{{ run.name }}</h1>
              <p>
                {{ formatDate(run.started_at) }} · v{{ run.version }} ·
                {{ run.dry_run ? '试运行' : '正式运行' }}
              </p>
            </div>
            <span class="status large" :class="run.status">{{ statusNames[run.status] }}</span>
          </div>
          <div class="run-progress">
            <div>
              <strong>{{ run.summary || run.error || '流程正在执行，请稍候…' }}</strong
              ><span>{{ run.progress }}%</span>
            </div>
            <progress max="100" :value="run.progress" /><button
              v-if="['running', 'cancelling'].includes(run.status)"
              :disabled="busy || run.status === 'cancelling'"
              @click="cancel"
            >
              {{ run.status === 'cancelling' ? '正在取消…' : '取消运行' }}
            </button>
            <p v-if="run.status === 'failed'" class="help">
              本次任务未自动重试。请根据下方日志检查输入或流程实现。
            </p>
          </div>
          <div class="run-grid">
            <section class="log-panel">
              <div class="section-heading">
                <h2>执行日志</h2>
                <span class="muted">保留最近 500 条</span>
              </div>
              <div class="logs" aria-label="执行日志">
                <p v-if="!run.logs.length" class="muted">等待流程输出…</p>
                <div v-for="(line, i) in run.logs" :key="i" :class="line.level">
                  <time>{{ new Date(line.at).toLocaleTimeString('zh-CN', { hour12: false }) }}</time
                  ><span>{{ line.message }}</span>
                </div>
              </div>
            </section>
            <section class="result-panel">
              <h2>运行结果</h2>
              <p v-if="!run.files.length" class="help">
                {{
                  run.status === 'succeeded'
                    ? '本次运行没有输出文件。'
                    : '流程成功完成后，结果文件将显示在这里。'
                }}
              </p>
              <a
                v-for="file in run.files"
                :key="file"
                class="artifact"
                :href="fileUrl(run.id, file)"
                download
                ><span>▤ {{ file }}</span
                ><strong>↓</strong></a
              >
              <details>
                <summary>本次配置</summary>
                <pre>{{ JSON.stringify(run.config, null, 2) }}</pre>
              </details>
              <small class="muted">敏感字段不会保存在运行记录中。</small>
            </section>
          </div>
        </template>

        <template v-else-if="page === 'guide'">
          <div class="page-heading">
            <div>
              <p class="eyebrow">BUILD WITH AI</p>
              <h1>把想法，变成可运行的流程。</h1>
              <p>描述你的工作，让 AI 按照统一规范制作流程包。</p>
            </div>
            <span class="local-badge">Skill Alpha</span>
          </div>
          <div class="guide-grid">
            <section>
              <span class="step-number">01</span>
              <h2>说明你要完成的工作</h2>
              <p>提供目标、输入样例、期望结果，以及运行环境。公开示例从合成数据开始。</p>
            </section>
            <section>
              <span class="step-number">02</span>
              <h2>让 AI 使用制作 Skill</h2>
              <p>将仓库中的流程制作 Skill 提供给你的 AI 开发工具，让它读取规范、生成代码并验证。</p>
              <code>skills/automaticworker-flow-author/SKILL.md</code>
            </section>
            <section>
              <span class="step-number">03</span>
              <h2>导入并验证结果</h2>
              <p>获取经过校验的 ZIP 包，导入工作台，检查配置并试运行，再用于正式工作。</p>
            </section>
          </div>
          <div class="guide-note">
            <h2>平台与流程，各司其职。</h2>
            <p>
              平台提供配置与运行能力，具体工作由流程包实现。导入的 Python
              流程具有本机执行能力，请使用可信来源的流程包。试运行的行为由流程作者实现。
            </p>
            <p>当前支持规范 1.0、Python 标准库与平台 SDK；外部依赖安装将在后续版本扩展。</p>
            <small>本地数据位置：{{ dataDir }}</small>
          </div>
        </template>
        <footer class="footer">
          AutoMaticWorker <span>开源平台 · 可扩展流程 · 为重复工作而生</span>
        </footer>
      </div>
    </main>

    <div v-if="showImport" class="modal-backdrop" @click.self="showImport = false">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="import-title">
        <div class="panel-heading">
          <h2 id="import-title">导入流程包</h2>
          <button class="icon-button" aria-label="关闭导入" @click="showImport = false">×</button>
        </div>
        <p>选择符合 AutoMaticWorker 规范的 ZIP 文件。</p>
        <div v-if="error" class="alert error" role="alert">{{ error }}</div>
        <label class="drop-zone"
          ><span>↑</span><strong>{{ importFile?.name || '选择 ZIP 流程包' }}</strong
          ><small>最大 20 MB · 最多 500 个文件</small
          ><input
            type="file"
            accept=".zip"
            aria-label="选择 ZIP 流程包"
            @change="importFile = chosenFile($event) || null" /></label
        ><label class="check-row"
          ><input v-model="replace" type="checkbox" />更新已有同 ID 流程（需要更高版本）</label
        ><label class="check-row"
          ><input
            v-model="trusted"
            type="checkbox"
          />我信任此流程包的来源，了解运行时会执行本机代码。</label
        ><button
          class="primary full"
          :disabled="busy || !importFile || !trusted"
          @click="importPackage"
        >
          {{ busy ? '正在校验并导入…' : '校验并导入' }}
        </button>
      </section>
    </div>
  </div>
</template>
