import PasswordRequirements from '../../../../src/js/components/password-requirements.js';

const states = new WeakMap();

export function initPasswordFeedback(root = document) {
  if (states.has(root)) return states.get(root);
  const element = root.querySelector('#password-preview-requirements');
  if (!element) return () => {};
  const instance = PasswordRequirements.getOrCreateInstance(element);
  // The catalog demonstrates readiness but never submits sample credentials.
  const preventSubmission = event => event.preventDefault();
  element.closest('form').addEventListener('submit', preventSubmission);
  instance.ready.catch(error => { setTimeout(() => { throw error; }, 0); });
  const dispose = () => {
    if (states.get(root) !== dispose) return;
    instance.dispose();
    element.closest('form').removeEventListener('submit', preventSubmission);
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}
