async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

export const startPipeline = ({
  agentName = '',
  projectName = '',
  customInstructions = '',
  sourceType = 'hub',
  agentFolder = '',
} = {}) =>
  request('/videos', {
    method: 'POST',
    body: JSON.stringify({
      agent_name: agentName,
      project_name: projectName,
      custom_instructions: customInstructions,
      source_type: sourceType,
      agent_folder: agentFolder,
    }),
  })

export const getStatus = (threadId) =>
  request(`/videos/${threadId}/status`)

export const resumePipeline = (threadId, action, scenes = []) =>
  request(`/videos/${threadId}/resume`, {
    method: 'POST',
    body: JSON.stringify({ action, scenes }),
  })
