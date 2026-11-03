<script setup lang="ts">
import { account } from '../../modules/identity/account';
import PeopleManagement from '../../modules/settings/people/PeopleManagement.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
</script>
<template><PeopleManagement v-if="account.user?.role === 'group_lead'" /><EmptyState v-else title="无人员管理权限" description="仅集团负责人可管理人员、角色和工厂范围。" icon="ShieldCheck" /></template>
