{{- define "uptime.name" -}}
{{ .Release.Name }}
{{- end }}

{{- define "uptime.labels" -}}
app.kubernetes.io/name: uptime-monitor
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "uptime.selector" -}}
app.kubernetes.io/name: uptime-monitor
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "uptime.secretName" -}}
{{ .Values.existingSecret | default (printf "%s-db" .Release.Name) }}
{{- end }}

{{- define "uptime.image" -}}
{{ .Values.image.repository }}:{{ .Values.image.tag }}
{{- end }}

{{/* settings shared by api and worker pods */}}
{{- define "uptime.podSecurity" -}}
enableServiceLinks: false
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
{{- end }}

{{- define "uptime.containerSecurity" -}}
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
{{- end }}
