<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps<{
  modelValue: string;
  options: string[];
  placeholder?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const isOpen = ref(false);
const selectRef = ref<HTMLDivElement | null>(null);

const displayValue = computed(() => {
  if (!props.modelValue) return props.placeholder || 'Todas';
  return props.modelValue;
});

function toggleDropdown() {
  isOpen.value = !isOpen.value;
}

function selectOption(option: string) {
  emit('update:modelValue', option);
  isOpen.value = false;
}

function handleClickOutside(event: MouseEvent) {
  if (selectRef.value && !selectRef.value.contains(event.target as Node)) {
    isOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <div ref="selectRef" class="custom-select" :class="{ open: isOpen }">
    <div class="select-trigger" @click="toggleDropdown">
      <span>{{ displayValue }}</span>
      <span class="arrow">▼</span>
    </div>
    <div v-if="isOpen" class="select-options">
      <div class="select-option" @click="selectOption('')">
        {{ placeholder || 'Todas' }}
      </div>
      <div
        v-for="option in options"
        :key="option"
        class="select-option"
        :class="{ selected: option === modelValue }"
        @click="selectOption(option)"
      >
        {{ option }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-select {
  position: relative;
  width: 100%;
  user-select: none;
  box-sizing: border-box;
}

.select-trigger {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(102, 239, 139, 0.35);
  color: #e6f7ff;
  border-radius: 8px;
  padding: 7px 10px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: border-color 0.2s;
  font-size: 14px;
  height: 38px;
  box-sizing: border-box;
  line-height: 1.4;
}

.custom-select.open .select-trigger,
.select-trigger:focus {
  border-color: #66ef8b;
  box-shadow: 0 0 0 2px rgba(102, 239, 139, 0.25);
  outline: none;
}

.arrow {
  font-size: 9px;
  transition: transform 0.2s;
  color: #a8bad2;
}

.custom-select.open .arrow {
  transform: rotate(180deg);
}

.select-options {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: rgba(10, 18, 31, 0.98);
  border: 1px solid rgba(102, 239, 139, 0.35);
  border-radius: 8px;
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.select-option {
  padding: 10px 12px;
  color: #e6f7ff;
  cursor: pointer;
  border-bottom: 1px solid rgba(120, 151, 189, 0.1);
  transition: none;
  font-size: 14px;
}

.select-option:last-child {
  border-bottom: none;
}

.select-option.selected {
  background: rgba(102, 239, 139, 0.1);
  color: #66ef8b;
  font-weight: 600;
}

/* Remove qualquer efeito de hover */
.select-option:hover {
  background: inherit;
  color: inherit;
}

.select-option.selected:hover {
  background: rgba(102, 239, 139, 0.1);
  color: #66ef8b;
}
</style>
