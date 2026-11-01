<script setup lang="ts">
import { ref, useId, watch } from 'vue';
import AppIcon from './AppIcon.vue';
const props = withDefaults(
  defineProps<{ open: boolean; title: string; kind?: 'dialog' | 'drawer' }>(),
  { kind: 'dialog' },
);
const emit = defineEmits<{ 'update:open': [value: boolean] }>();
const dialog = ref<HTMLDialogElement>();
const titleId = useId();
function backdrop(event: MouseEvent) {
  if (event.target === dialog.value) emit('update:open', false);
}
function keepFocusInside(event: KeyboardEvent) {
  if (event.key !== 'Tab' || !dialog.value?.open) return;
  const controls = [
    ...dialog.value.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]',
    ),
  ].filter(
    (element) =>
      element.tabIndex >= 0 && !element.matches(':disabled') && element.getClientRects().length > 0,
  );
  const first = controls[0];
  const last = controls.at(-1);
  if (!first || !last) {
    event.preventDefault();
    dialog.value.focus();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
watch(
  [() => props.open, dialog],
  () => {
    if (props.open && dialog.value && !dialog.value.open) dialog.value.showModal();
    else if (!props.open && dialog.value?.open) dialog.value.close();
  },
  { flush: 'post', immediate: true },
);
</script>
<template>
  <dialog
    ref="dialog"
    :class="['app-overlay', kind]"
    :aria-labelledby="titleId"
    @close="emit('update:open', false)"
    @click="backdrop"
    @keydown="keepFocusInside"
  >
    <div class="overlay-inner">
      <header class="overlay-header">
        <h2 :id="titleId">{{ title }}</h2>
        <button
          type="button"
          class="icon-button"
          aria-label="关闭"
          @click="emit('update:open', false)"
        >
          <AppIcon name="X" />
        </button>
      </header>
      <div class="overlay-body"><slot /></div>
      <footer v-if="$slots.footer" class="overlay-footer"><slot name="footer" /></footer>
    </div>
  </dialog>
</template>
