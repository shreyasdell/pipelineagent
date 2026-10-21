{{- define "sglang-model-serving.sanitizeLabel" }}
{{- $value := . }}
{{- $value = $value | lower }}
{{- $value = $value | replace "/" "-" }}
{{- $value = $value | replace "_" "-" }}
{{- $value = $value | replace "." "-" }}
{{- $value = regexReplaceAll "[^a-z0-9-]" $value "-" }}
{{- $value = trimAll "-" $value }}
{{- $value = trunc 63 $value }}
{{- $value }}
{{- end }}
