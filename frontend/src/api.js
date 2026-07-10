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

export const startPipeline = (agentId, projectId, customInstructions) =>
  request('/videos', {
    method: 'POST',
    body: JSON.stringify({
      agent_id: agentId,
      project_id: projectId,
      custom_instructions: customInstructions,
    }),
  })

export const getStatus = (threadId) =>
  request(`/videos/${threadId}/status`)

export const resumePipeline = (threadId, action, scenes = []) =>
  request(`/videos/${threadId}/resume`, {
    method: 'POST',
    body: JSON.stringify({ action, scenes }),
  })
