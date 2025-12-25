<template>
  <h3 :class="cn('text-2xl font-semibold leading-none tracking-tight', className)">
    <slot />
  </h3>
</template>

<script setup>
import { cn } from "@/lib/utils"

const props = defineProps({
  class: {
    type: String,
    default: "",
  },
})

const className = props.class || ""
</script>
