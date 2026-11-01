const instances = new WeakMap();

function strip(value, characters) {
  const points = Array.from(value);
  let start = 0;
  let end = points.length;
  while (start < end && characters.includes(points[start])) start++;
  while (end > start && characters.includes(points[end - 1])) end--;
  return points.slice(start, end).join("");
}

// Hosts supply a versioned policy. Only explicit host analyzers receive values;
// Core performs no credential submission, persistence or strength estimation.
export function passwordRequirementStates(value, policy) {
  const normalized = strip(value.normalize("NFKC"), policy.whitespace);
  const maximum = Math.max(Array.from(value).length, Array.from(value.normalize("NFKC")).length) <= policy.maxlength;
  const checks = {
    length: Math.min(Array.from(strip(value, policy.whitespace)).length, Array.from(normalized).length) >= policy.minlength,
    case: /\p{Uppercase}/u.test(normalized) && /\p{Lowercase}/u.test(normalized),
    number: /\p{Nd}/u.test(normalized),
    symbol: /[\p{P}\p{S}]/u.test(normalized),
    maximum,
  };
  return policy.rules.map(rule => ({key: rule.key, label: rule.label, warning: Boolean(rule.warning), met: Boolean(checks[rule.key])}));
}

export default class PasswordRequirements {
  static getInstance(element) { return instances.get(element) || null; }
  static getOrCreateInstance(element, options) {
    return this.getInstance(element) || new this(element, options);
  }

  constructor(element, options = {}) {
    if (!element?.matches('fieldset[data-password-requirements]') || !element.id) {
      throw new TypeError('PasswordRequirements requires an identified Fieldset.');
    }
    const existing = instances.get(element);
    if (existing) return existing;
    const configuration = JSON.parse(element.dataset.passwordRequirements);
    const document = element.ownerDocument;
    const owner = element.closest('.moo-ui');
    const input = document.getElementById(configuration.input);
    const confirmation = configuration.confirmation && document.getElementById(configuration.confirmation);
    const localControl = node => node?.matches('input[type="password"]') && node.closest('.moo-ui') === owner && node.form === element.closest('form');
    const policy = configuration.policy;
    if (!owner || !localControl(input) || (configuration.confirmation && !localControl(confirmation)) ||
        policy?.version !== 3 || !Number.isInteger(policy.minlength) || policy.minlength < 1 ||
        !Number.isInteger(policy.maxlength) || policy.maxlength < policy.minlength || policy.maxlength > 128 ||
        !Array.isArray(policy.rules) || !policy.rules.length ||
        policy.rules.some(rule => !['length', 'case', 'number', 'symbol', 'maximum'].includes(rule.key) || typeof rule.label !== 'string' ||
          (rule.warning !== undefined && typeof rule.warning !== 'boolean')) ||
        new Set(policy.rules.map(rule => rule.key)).size !== policy.rules.length ||
        !['length', 'maximum'].every(key => policy.rules.some(rule => rule.key === key)) ||
        typeof policy.whitespace !== 'string' ||
        (options.analyze !== undefined && typeof options.analyze !== 'function')) {
      throw new TypeError('PasswordRequirements requires same-owner controls and a versioned public policy.');
    }
    this._element = element;
    this._originals = new Map();
    this._listeners = [];
    const local = suffix => {
      const node = document.getElementById(element.id + '-' + suffix);
      if (!node || !element.contains(node)) throw new TypeError('Missing local requirement description.');
      this._originals.set(node, {text: node.textContent, className: node.className, hidden: node.hidden});
      return node;
    };
    const rows = new Map(policy.rules.map(rule => [rule.key, local(rule.key)]));
    const summary = local('summary');
    const match = confirmation && local('confirmation');
    const hint = configuration.submit && document.getElementById(element.id + '-submit-hint');
    const submit = configuration.submit && document.getElementById(configuration.submit);
    if (configuration.submit && (!input.form || !hint?.matches('[data-bs-toggle="tooltip"]') || !element.contains(hint) ||
        !submit?.matches('button[type="submit"], input[type="submit"]') || submit.closest('.moo-ui') !== owner || submit.form !== input.form)) {
      throw new TypeError('PasswordRequirements requires a same-form submit Tooltip.');
    }
    const initialDisabled = submit?.disabled;
    const initialTabIndex = hint?.getAttribute('tabindex');
    const initialTitle = hint?.getAttribute('data-bs-title');
    const initialRole = hint?.getAttribute('role');
    const initialLabel = hint?.getAttribute('aria-label');
    const initialHidden = hint?.hidden;
    const restoreAttribute = (name, value) => {
      if (value === null) hint.removeAttribute(name);
      else hint.setAttribute(name, value);
    };
    const submitParent = submit?.parentNode;
    const submitNext = submit?.nextSibling;
    const hintParent = hint?.parentNode;
    const hintNext = hint?.nextSibling;
    const hintChildren = hint && [...hint.childNodes];
    const view = document.defaultView;
    const Tooltip = view.bootstrap?.Tooltip || view.Tooltip;
    if (submit && (!Tooltip || typeof Tooltip.getInstance !== 'function' ||
        typeof Tooltip.getOrCreateInstance !== 'function')) {
      throw new TypeError('PasswordRequirements submit binding requires Bootstrap Tooltip.');
    }
    const previousTooltip = hint && Tooltip?.getInstance(hint);
    let tooltip;
    let gateReady = !submit;
    let lastTitle;
    if (submit) {
      this._listeners.push(() => {
        submit.disabled = initialDisabled;
        if (initialTabIndex === null) hint.removeAttribute('tabindex');
        else hint.setAttribute('tabindex', initialTabIndex);
        restoreAttribute('data-bs-title', initialTitle);
        restoreAttribute('role', initialRole);
        restoreAttribute('aria-label', initialLabel);
        tooltip?.hide();
        if (!previousTooltip) tooltip?.dispose();
        else { tooltip.enable(); tooltip.setContent({'.tooltip-inner': initialTitle}); }
        submitParent.insertBefore(submit, submitNext?.parentNode === submitParent ? submitNext : null);
        hintParent.insertBefore(hint, hintNext?.parentNode === hintParent ? hintNext : null);
        hint.replaceChildren(...hintChildren);
        hint.hidden = initialHidden;
      });
    }
    const updateSubmit = states => {
      if (!submit) return;
      gateReady = Boolean(input.value) && states.every(state => state.met);
      submit.disabled = !gateReady;
      hint.tabIndex = gateReady ? -1 : 0;
      restoreAttribute('role', gateReady ? null : initialRole);
      restoreAttribute('aria-label', gateReady ? null : initialLabel);
      const title = states.filter(state => !state.met && (input.value || !state.warning || state.key === 'confirmation'))
        .map(state => state.label).join(' ');
      hint.setAttribute('data-bs-title', title || initialTitle);
      if (gateReady) { tooltip?.hide(); tooltip?.disable(); }
      else {
        tooltip?.enable();
        if (title !== lastTitle) tooltip?.setContent({'.tooltip-inner': title || initialTitle});
      }
      lastTitle = title;
    };
    const show = (node, label, met, warning = false, active = Boolean(input.value)) => {
      node.textContent = warning ? label : (met ? '✓ ' : '— ') + label;
      node.hidden = warning && (!active || met);
      node.classList.toggle('text-body', !warning && met);
      node.classList.toggle('text-danger', warning);
      node.dataset.requirementMet = String(met);
    };
    const update = () => {
      // A failing host analyzer/callback must not leave a previously open gate.
      gateReady = !submit;
      if (submit) submit.disabled = true;
      const states = passwordRequirementStates(input.value, policy);
      const withinMaximum = Math.max(Array.from(input.value).length,
        Array.from(input.value.normalize('NFKC')).length) <= policy.maxlength;
      // Analysis is explicitly host-supplied. Core never imports an estimator.
      let analysis = null;
      const analysisValue = strip(input.value.normalize('NFKC'), policy.whitespace);
      if (options.analyze && analysisValue && withinMaximum) {
        analysis = options.analyze(analysisValue);
        if (!analysis || typeof analysis.met !== 'boolean' ||
            !Number.isInteger(analysis.score) || analysis.score < 0 || analysis.score > 4) {
          throw new TypeError('Password analysis must synchronously return {met: boolean, score: 0..4}.');
        }
      }
      if (options.analyze) states.push({key: 'analysis', label: 'Host password analysis must pass.',
        met: Boolean(analysis?.met), warning: true});
      if (confirmation) states.push({key: 'confirmation', label: this._originals.get(match).text,
        warning: true, met: Boolean(confirmation.value) && confirmation.value === input.value});
      for (const state of states.filter(state => state.key !== 'analysis')) show(state.key === 'confirmation' ? match : rows.get(state.key), state.label,
        Boolean(input.value) && state.met, state.warning, state.key === 'confirmation' ? Boolean(confirmation.value) : Boolean(input.value));
      const missing = states.filter(state => !state.met).length;
      const warnings = states.filter(state => state.warning && !state.met).map(state => state.label).join(' ');
      const summaryText = !input.value ? this._originals.get(summary).text : missing ? `Remaining: ${missing} ${warnings}`.trim() : 'Shown checks met. Final validation happens on submit.';
      if (summary.textContent !== summaryText) summary.textContent = summaryText;
      // The host owns the strength source. Only non-secret Boolean check states
      // leave the component; no password value is passed to a callback/event.
      options.onChange?.(states.map(({key, met}) => ({key, met: Boolean(input.value) && met})), Boolean(input.value), analysis?.score ?? null);
      updateSubmit(states);
    };
    instances.set(element, this);
    try {
      if (submit) {
        submitParent.insertBefore(hint, submit);
        hint.replaceChildren(submit);
        hint.hidden = false;
        submit.disabled = true;
        tooltip = Tooltip?.getOrCreateInstance(hint, {container: owner, html: false, trigger: 'hover focus'});
      }
      for (const node of [input, confirmation].filter(Boolean)) {
        for (const event of ['input', 'change']) {
          node.addEventListener(event, update);
          this._listeners.push(() => node.removeEventListener(event, update));
        }
      }
      if (input.form) {
        if (submit) {
          const guard = event => {
            try { update(); } catch (error) {
              event.preventDefault();
              event.stopImmediatePropagation();
              throw error;
            }
            if (!gateReady) { event.preventDefault(); event.stopImmediatePropagation(); hint.focus(); }
          };
          input.form.addEventListener('submit', guard, true);
          this._listeners.push(() => input.form.removeEventListener('submit', guard, true));
        }
        const reset = () => {
          clearTimeout(this._resetTimer);
          this._resetTimer = setTimeout(update, 0);
        };
        input.form.addEventListener('reset', reset);
        this._listeners.push(() => input.form.removeEventListener('reset', reset));
      }
      update();
      element.dataset.requirementsReady = 'true';
      this.ready = Promise.resolve(this);
    } catch (error) {
      this.dispose();
      throw error;
    }
  }

  dispose() {
    if (instances.get(this._element) !== this) return;
    clearTimeout(this._resetTimer);
    for (const remove of this._listeners.splice(0)) remove();
    for (const [node, original] of this._originals) {
      node.textContent = original.text;
      node.className = original.className;
      node.hidden = original.hidden;
      delete node.dataset.requirementMet;
    }
    delete this._element.dataset.requirementsReady;
    instances.delete(this._element);
    this._originals.clear();
  }
}
