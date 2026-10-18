/* Explicit, per-account provider connections. No automatic consent or sending. */
(()=>{
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const names={gmail:'Gmail',icloud:'iCloud Mail',microsoft365:'Microsoft 365',hotmail:'Outlook / Hotmail'};
  const labels={connected:'Cloud access checked',saved_sign_in:'Sign-in saved · check inbox',sign_in_needed:'Sign-in needed',unavailable:'Connection needs attention'};
  async function mount(target,{api,onOpen,notify=()=>{}}){
    let disposed=false;
    target.classList.add('mail-account-settings');
    async function refresh(){
      try{
        const data=await api('/v1/workspace/mail-accounts');
        if(disposed||!target.isConnected)return;
        target.innerHTML=`<div class="section-heading"><div><h2>Your mail accounts</h2><p>Connect each inbox directly. Mac-synced mail remains available separately.</p></div><button type="button" class="secondary" data-account-refresh>Refresh status</button></div><details class="mail-add-account"><summary>Add an email account</summary><form data-add-account><label>Email provider<select name="provider"><option value="microsoft365">Microsoft 365 / work email</option><option value="hotmail">Outlook / Hotmail</option><option value="gmail">Gmail / Google Workspace</option><option value="icloud">iCloud Mail</option></select></label><label>Email address<input name="address" type="email" autocomplete="email" maxlength="254" required placeholder="you@example.com"></label><p>This adds an inbox to this private workspace. Complete the provider sign-in next. Enter verification codes on the provider’s own page.</p><button>Add and connect</button><p role="status" aria-live="polite"></p></form></details><div class="mail-account-grid">${data.accounts.map(account=>`<article class="mail-account-card"><div class="mail-account-provider">${esc(names[account.provider]||account.provider)}</div><h3>${esc(account.address)}</h3><span class="badge ${account.state==='connected'?'good':'warn'}">${esc(labels[account.state]||account.state)}</span><p>${esc(account.detail)}</p>${account.checked_at?`<small>Last checked ${esc(new Date(account.checked_at).toLocaleString('en-GB'))}</small>`:''}<div class="actions"><button type="button" data-account-connect="${esc(account.id)}" class="${account.can_open?'secondary':''}">${account.can_open?'Reconnect':'Connect account'}</button>${account.can_open?`<button type="button" data-account-open="${esc(account.id)}">Open cloud inbox</button>`:''}<a href="${esc(account.webmail_url)}" target="_blank" rel="noopener noreferrer">Open mail app ↗</a></div></article>`).join('')}</div><p class="muted">These connections read your provider's inbox and its read/unread flags. Reading here does not mark messages read. Outgoing messages open in the mail app for your final Send.</p>`;
        target.querySelector('[data-account-refresh]').onclick=refresh;
        target.querySelector('[data-add-account]').onsubmit=async event=>{
          event.preventDefault();const form=event.currentTarget,button=form.querySelector('button'),status=form.querySelector('[role=status]');
          button.disabled=true;
          try{const added=await api('/v1/workspace/mail-accounts',{address:form.elements.address.value,provider:form.elements.provider.value});await refresh();const updated=await api('/v1/workspace/mail-accounts');const account=updated.accounts.find(a=>a.id===added.id);if(account)await connect(account);}
          catch(error){status.textContent=error.message||'Account could not be added.';}
          finally{button.disabled=false;}
        };
        target.querySelectorAll('[data-account-connect]').forEach(button=>button.onclick=()=>connect(data.accounts.find(a=>a.id===button.dataset.accountConnect)));
        target.querySelectorAll('[data-account-open]').forEach(button=>button.onclick=()=>onOpen?.(data.accounts.find(a=>a.id===button.dataset.accountOpen)));
      }catch(error){if(!disposed)target.textContent=error.message||'Account settings could not be loaded.';}
    }
    function makeDialog(account){
      const dialog=document.createElement('dialog');dialog.className='mail-connect-dialog';
      dialog.innerHTML=`<form method="dialog" class="mail-connect-close"><button class="secondary" aria-label="Close account connection">Close ×</button></form><h2>Connect ${esc(names[account.provider])}</h2><p><strong>${esc(account.address)}</strong></p><div class="mail-connect-body"></div>`;
      document.body.append(dialog);dialog.showModal();
      dialog.addEventListener('close',()=>dialog.remove(),{once:true});
      return dialog;
    }
    async function connect(account){
      const dialog=makeDialog(account),body=dialog.querySelector('.mail-connect-body');
      if(account.method==='app_password'){
        const apple=account.provider==='icloud';
        const providerSteps=apple
          ? `<p>Apple requires two-factor authentication for app-specific passwords. On <strong>Sign-In &amp; Security</strong>, scroll to <strong>App-Specific Passwords</strong>, create one named <strong>JJRVIS</strong>, then paste only the generated password below.</p><p><a href="${esc(account.sign_in_url)}" target="_blank" rel="noopener noreferrer">Open Apple Sign-In &amp; Security ↗</a> <a href="https://support.apple.com/en-gb/102654" target="_blank" rel="noopener noreferrer">Apple instructions ↗</a></p>`
          : `<p>If Google offers App Passwords for this account, generate one named <strong>JJRVIS</strong> and enter it below. Google requires 2-Step Verification. <strong>Do not enter your normal Google password or an Authenticator code.</strong></p><p>If Google says this setting is unavailable, this connection cannot finish using an app password. Mac-synced mail remains a separate option; Google OAuth is not configured here yet.</p><p><a href="${esc(account.sign_in_url)}" target="_blank" rel="noopener noreferrer">Open Google App Passwords ↗</a> · <a href="https://support.google.com/accounts/answer/185833?hl=en-GB" target="_blank" rel="noopener noreferrer">Google instructions ↗</a></p>`;
        body.innerHTML=`${providerSteps}<form class="mail-password-form" ><label>App-specific password<input type="password" name="app_password" autocomplete="new-password" minlength="16" maxlength="64" placeholder="16-character app password" required></label><p class="muted">Use the password created specifically for JJRVIS. It is checked with the provider and saved privately on this Mac only after it is accepted.</p><button>Verify and connect</button><p role="status" aria-live="polite"></p></form>`;
        const form=body.querySelector('form');
        form.onsubmit=async event=>{
          event.preventDefault();const button=form.querySelector('button'),input=form.querySelector('input'),status=form.querySelector('[role=status]');
          button.disabled=true;status.textContent='Checking secure inbox access…';
          try{await api(`/v1/workspace/mail-accounts/${encodeURIComponent(account.id)}/app-password`,{app_password:input.value});input.value='';status.textContent='Cloud inbox connection verified.';await refresh();window.dispatchEvent(new CustomEvent('jjrvis-mail-accounts-changed'));notify('Account connected. Open its cloud inbox to read messages.');dialog.close();}
          catch(error){status.textContent=error.message||'The account could not be connected.';}
          finally{input.value='';button.disabled=false;}
        };
        return;
      }
      body.innerHTML='<p role="status" aria-live="polite">Preparing Microsoft sign-in…</p>';
      try{
        const result=await api(`/v1/workspace/mail-accounts/${encodeURIComponent(account.id)}/microsoft`,{});
        if(!dialog.isConnected)return;
        body.innerHTML=`<p>Sign in with <strong>${esc(account.address)}</strong> and enter this code. Only inbox reading is requested.</p><p class="mail-sign-in-code">${esc(result.user_code)}</p><p><a class="mail-provider-link" href="${esc(result.verification_uri)}" target="_blank" rel="noopener noreferrer">Continue to Microsoft ↗</a></p><p role="status" aria-live="polite">Waiting for you to finish sign-in…</p>`;
        const poll=async()=>{
          if(!dialog.isConnected||disposed)return;
          try{
            const state=await api(`/v1/workspace/mail-sign-ins/${encodeURIComponent(result.job_id)}`);
            if(!dialog.isConnected)return;
            body.querySelector('[role=status]').textContent=state.detail;
            if(state.state==='pending')setTimeout(poll,4000);
            else if(state.state==='connected'){await refresh();window.dispatchEvent(new CustomEvent('jjrvis-mail-accounts-changed'));notify('Microsoft account identity and inbox access verified.');}
          }catch(error){if(dialog.isConnected)body.querySelector('[role=status]').textContent=error.message||'Sign-in expired. Close this window and start again.';}
        };
        setTimeout(poll,4000);
      }catch(error){body.querySelector('[role=status]').textContent=error.message||'Microsoft sign-in could not start.';}
    }
    await refresh();
    return {refresh,destroy(){disposed=true;}};
  }
  window.JJMailAccounts={mount};
})();
