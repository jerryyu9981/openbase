import eslintPluginVue from 'eslint-plugin-vue'
import tsParser from '@typescript-eslint/parser'
import vueParser from 'vue-eslint-parser'

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
  ...eslintPluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{ts,vue}', 'tests/**/*.ts'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 2022,
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/html-self-closing': 'off',
      'vue/no-v-html': 'off',
      'vue/no-unused-vars': 'off',
      'vue/require-default-prop': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'no-unused-vars': 'off',
    },
  },
]
