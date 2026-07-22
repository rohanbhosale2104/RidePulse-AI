/**
 * Shared frontend utilities: auth guard, authenticated fetch wrappers,
 * and navbar username / logout wiring.
 */

function getToken() {
  return localStorage.getItem('access_token');
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = '/login';
  }
}

function setUsernameLabel() {
  const label = document.getElementById('usernameLabel');
  const username = localStorage.getItem('username');
  if (label && username) {
    label.textContent = username;
  }
}

async function apiGet(url) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (res.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  const data = await res.json();
  if (!res.ok) {
    const message = typeof data.detail === 'string'
      ? data.detail
      : Array.isArray(data.detail)
        ? data.detail.map(d => d.msg).join(', ')
        : 'Request failed';
    throw new Error(message);
  }
  return data;
}

document.addEventListener('DOMContentLoaded', () => {
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('access_token');
      localStorage.removeItem('username');
      window.location.href = '/login';
    });
  }
  setUsernameLabel();
});
