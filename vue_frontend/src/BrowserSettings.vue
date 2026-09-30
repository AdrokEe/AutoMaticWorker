<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from './api'
interface Settings {
  backend: string; executable_path: string; headless: boolean; profile: string
  cdp_url: string; input_mode: string; interaction: string
}
interface Report { settings: Settings; ready: boolean; errors: string[]; versions: Record<string, string>; note: string }
const props = defineProps<{ active: boolean }>()
const report = ref<Report | null>(null)
const config = ref<Settings>({ backend: 'playwright', executable_path: '', headless: false, profile: '', cdp_url: '', input_mode: 'browser', interaction: 'natural' })
const error = ref('')
const busy = ref(false)
const saved = ref(false)
async function load(save = false) {
  error.value = ''; busy.value = true; saved.value = false
  try {
    report.value = await api<Report>('/environment', save ? 'PUT' : 'GET', save ? config.value : undefined)
    config.value = { ...report.value.settings }; saved.value = save
  } catch (e) { error.value = e instanceof Error ? e.message : String(e) }
  finally { busy.value = false }
}
onMounted(() => load())
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">LOCAL BROWSER</p><h1>浏览器环境</h1><p>使用已经准备好的本地组件，配置和运行均不下载文件。</p></div></div>
  <div class="environment-panel">
    <div v-if="error" class="alert error" role="alert">{{ error }}</div>
    <div v-if="saved" class="alert success" role="status">配置已保存。{{ report?.ready ? '本地组件检查通过。' : '请根据下方提示补齐组件。' }}</div>
    <p v-if="props.active" class="help">任务运行期间不能更改环境。</p>
    <form @submit.prevent="load(true)">
      <fieldset :disabled="busy || props.active">
        <label>浏览器后端<select v-model="config.backend"><option value="playwright">Playwright（标准）</option><option value="patchright">Patchright（可选）</option></select></label>
        <label>本地浏览器可执行文件<input v-model="config.executable_path" placeholder="C:\Program Files\Google\Chrome\Application\chrome.exe" autocomplete="off"></label>
        <p class="help">填写本机 Chromium、Chrome 或 Edge 的完整路径。缺少 Python 组件时，请由部署人员使用离线材料安装。</p>
        <label>输入模式<select v-model="config.input_mode"><option value="browser">浏览器内模拟（不占用系统鼠标）</option><option value="desktop">Windows 系统鼠标键盘（占用桌面）</option></select></label>
        <label>交互节奏<select v-model="config.interaction"><option value="natural">曲线移动与逐字输入</option><option value="direct">直接移动与快速逐字输入</option></select></label>
        <label class="check-row"><input v-model="config.headless" type="checkbox">不显示浏览器窗口（人工登录、系统输入不可用）</label>
        <label>保留登录状态的目录名称<input v-model="config.profile" placeholder="留空使用临时会话，如填写 demo-login 则保留状态" autocomplete="off"></label>
        <p class="help">登录状态只保存在本机；同一目录不能同时使用。不要填写日常浏览器的数据目录。</p>
        <details><summary>接管已启动的本机浏览器</summary><label>调试地址<input v-model="config.cdp_url" placeholder="http://127.0.0.1:9222" autocomplete="off"></label><p class="help">由部署人员准备调试端口。接管时留空登录目录并关闭无头模式；流程使用新标签页，不操作原有标签页。</p></details>
        <button class="primary" type="submit">保存并检查本地环境</button>
      </fieldset>
    </form>
    <section v-if="report" class="environment-report" aria-label="环境检查结果">
      <h2>{{ report.ready ? '本地组件已就绪' : '还需准备组件' }}</h2>
      <ul v-if="report.errors.length"><li v-for="item in report.errors" :key="item">{{ item }}</li></ul>
      <p v-for="(value, key) in report.versions" :key="key">{{ key }} · {{ value }}</p>
      <small>{{ report.note }}</small>
    </section>
  </div>
</template>

<style scoped>
.environment-panel{max-width:850px;padding:28px;background:white;border:1px solid #dce5df;border-radius:16px}
fieldset{border:0;padding:0;margin:0}label:not(.check-row){display:block;margin:18px 0;font-weight:600}
input:not([type=checkbox]),select{display:block;width:100%;padding:12px;margin-top:8px;border:1px solid #bdcbc2;border-radius:8px;font:inherit;box-sizing:border-box}
details{margin:22px 0}button{margin-top:20px}.environment-report{border-top:1px solid #dce5df;margin-top:24px;padding-top:20px}.environment-report li{margin:10px 0}
</style>
