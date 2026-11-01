<script setup lang="ts">
import { useId } from 'vue';
const props = defineProps<{ items: string[]; modelValue: string; label: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const id = useId();
function move(event: KeyboardEvent, index: number) {
  let next = index;
  if (event.key === 'ArrowRight') next = (index + 1) % props.items.length;
  else if (event.key === 'ArrowLeft') next = (index - 1 + props.items.length) % props.items.length;
  else if (event.key === 'Home') next = 0;
  else if (event.key === 'End') next = props.items.length - 1;
  else return;
  event.preventDefault();
  emit('update:modelValue', props.items[next]!);
  document.getElementById(`${id}-tab-${next}`)?.focus();
}
</script>
<template>
  <div class="tabs" role="tablist" :aria-label="label">
    <button
      v-for="(item, index) in items"
      :id="`${id}-tab-${index}`"
      :key="item"
      type="button"
      role="tab"
      :aria-selected="modelValue === item"
      :aria-controls="`${id}-panel`"
      :tabindex="modelValue === item ? 0 : -1"
      :class="{ selected: modelValue === item }"
      @click="emit('update:modelValue', item)"
      @keydown="move($event, index)"
    >
      {{ item }}
    </button>
  </div>
  <div
    :id="`${id}-panel`"
    class="tab-panel"
    role="tabpanel"
    :aria-labelledby="`${id}-tab-${items.indexOf(modelValue)}`"
    tabindex="0"
  >
    <slot />
  </div>
</template>
