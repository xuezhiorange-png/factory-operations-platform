<script setup lang="ts">
import { account } from './account';
</script>
<template>
  <aside v-if="account.status === 'pending'" class="asset-source-notice synthetic" role="status">
    账号待授权：身份已识别，尚未获得有效角色及工厂范围。
  </aside>
</template>
