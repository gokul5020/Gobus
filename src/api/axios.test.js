import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import api from './axios';

describe('api axios instance', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('points at the backend base URL', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:5000/api');
  });

  it('attaches the bearer token from localStorage on requests', () => {
    localStorage.setItem('token', 'abc123');
    const handler = api.interceptors.request.handlers[0].fulfilled;
    const config = handler({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer abc123');
  });

  it('does not attach an auth header when no token is stored', () => {
    const handler = api.interceptors.request.handlers[0].fulfilled;
    const config = handler({ headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });
});
