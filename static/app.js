(() => {
  const users = ["belen@ajaia.test", "alex@ajaia.test", "sam@ajaia.test"];
  const switcher = document.getElementById("user-switcher");
  const avatar = document.getElementById("user-avatar");
  const ownedList = document.getElementById("owned-documents");
  const sharedList = document.getElementById("shared-documents");
  const welcome = document.getElementById("welcome");
  const editorView = document.getElementById("editor-view");
  const titleInput = document.getElementById("document-title");
  const saveState = document.getElementById("save-state");
  const modal = document.getElementById("share-modal");
  const shareSelect = document.getElementById("share-user");
  const shareList = document.getElementById("share-list");
  const shareError = document.getElementById("share-error");
  let currentUser = null;
  let activeDocument = null;
  let ownedDocuments = [];
  let sharedDocuments = [];
  let contentSaveTimer = null;
  let titleSaveTimer = null;
  let toastTimer = null;
  let quill;

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...options.headers },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
    return data;
  }

  function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 2500);
  }

  function setSaveState(state, message) {
    saveState.className = `save-state${state ? ` ${state}` : ""}`;
    saveState.innerHTML = `<span class="save-dot"></span> ${message}`;
  }

  function renderList() {
    const renderGroup = (element, documents, emptyId) => {
      element.replaceChildren();
      documents.forEach((doc) => {
        const button = window.document.createElement("button");
        button.className = `doc-link${activeDocument?.id === doc.id ? " active" : ""}`;
        button.type = "button";
        button.innerHTML = '<span class="doc-icon" aria-hidden="true">▤</span>';
        const name = window.document.createElement("span");
        name.className = "doc-name";
        name.textContent = doc.title;
        button.append(name);
        button.addEventListener("click", () => openDocument(doc.id));
        element.append(button);
      });
      document.getElementById(emptyId).hidden = documents.length > 0;
    };
    renderGroup(ownedList, ownedDocuments, "owned-empty");
    renderGroup(sharedList, sharedDocuments, "shared-empty");
    document.getElementById("owned-count").textContent = ownedDocuments.length;
    document.getElementById("shared-count").textContent = sharedDocuments.length;
  }

  async function refreshDocuments() {
    const data = await api("/api/documents");
    ownedDocuments = data.owned;
    sharedDocuments = data.shared;
    renderList();
  }

  async function openDocument(id) {
    try {
      const { document: doc } = await api(`/api/documents/${id}`);
      activeDocument = doc;
      welcome.hidden = true;
      editorView.hidden = false;
      titleInput.value = doc.title;
      titleInput.readOnly = !doc.is_owner;
      window.document.getElementById("document-location").textContent = doc.is_owner ? "My Documents" : "Shared with Me";
      window.document.getElementById("document-owner").textContent = doc.is_owner ? "Owned by you" : `Owned by ${doc.owner_email}`;
      window.document.getElementById("document-updated").textContent = `Updated ${new Date(doc.updated_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`;
      window.document.getElementById("share-button").hidden = !doc.is_owner;
      quill.setContents([]);
      if (doc.content) quill.clipboard.dangerouslyPasteHTML(doc.content);
      renderList();
      setSaveState("", "All changes saved");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function saveDocument(changes, documentId = activeDocument?.id) {
    if (!documentId) return;
    if (activeDocument?.id === documentId) setSaveState("saving", "Saving…");
    try {
      const { document: doc } = await api(`/api/documents/${documentId}`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      if (activeDocument?.id === documentId) {
        activeDocument = doc;
        setSaveState("", "All changes saved");
      }
      await refreshDocuments();
    } catch (error) {
      if (activeDocument?.id === documentId) setSaveState("error", "Could not save");
      showToast(error.message);
    }
  }

  function scheduleContentSave() {
    if (!activeDocument) return;
    const documentId = activeDocument.id;
    const content = quill.root.innerHTML;
    setSaveState("saving", "Unsaved changes");
    clearTimeout(contentSaveTimer);
    contentSaveTimer = setTimeout(() => saveDocument({ content }, documentId), 650);
  }

  async function createDocument(title = "Untitled document", content = "") {
    try {
      const { document: doc } = await api("/api/documents", {
        method: "POST",
        body: JSON.stringify({ title, content }),
      });
      await refreshDocuments();
      await openDocument(doc.id);
      if (title === "Untitled document") {
        titleInput.focus();
        titleInput.select();
      }
    } catch (error) {
      showToast(error.message);
    }
  }

  async function switchUser(email) {
    try {
      await api("/api/session", { method: "POST", body: JSON.stringify({ email }) });
      currentUser = email;
      avatar.textContent = email[0].toUpperCase();
      activeDocument = null;
      await refreshDocuments();
      welcome.hidden = false;
      editorView.hidden = true;
    } catch (error) {
      showToast(error.message);
    }
  }

  async function openShareModal() {
    if (!activeDocument?.is_owner) return;
    shareError.textContent = "";
    shareSelect.replaceChildren();
    users.filter((email) => email !== currentUser).forEach((email) => {
      const option = window.document.createElement("option");
      option.value = email;
      option.textContent = email;
      shareSelect.append(option);
    });
    modal.hidden = false;
    await refreshShares();
  }

  async function refreshShares() {
    try {
      const { shared_with: sharedWith } = await api(`/api/documents/${activeDocument.id}/shares`);
      shareList.replaceChildren();
      if (!sharedWith.length) {
        const empty = window.document.createElement("li");
        empty.className = "no-shares";
        empty.textContent = "Only you have access so far.";
        shareList.append(empty);
      }
      sharedWith.forEach((email) => {
        const item = window.document.createElement("li");
        const person = window.document.createElement("span");
        person.className = "share-person";
        person.textContent = email[0].toUpperCase();
        const label = window.document.createElement("span");
        label.textContent = email;
        const remove = window.document.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove ${email}`);
        remove.addEventListener("click", () => removeShare(email));
        item.append(person, label, remove);
        shareList.append(item);
      });
    } catch (error) {
      shareError.textContent = error.message;
    }
  }

  async function removeShare(email) {
    try {
      await api(`/api/documents/${activeDocument.id}/shares`, {
        method: "DELETE",
        body: JSON.stringify({ email }),
      });
      await refreshShares();
      await refreshDocuments();
      showToast("Access removed");
    } catch (error) {
      shareError.textContent = error.message;
    }
  }

  document.getElementById("new-document").addEventListener("click", () => createDocument());
  document.getElementById("welcome-create").addEventListener("click", () => createDocument());
  switcher.addEventListener("change", () => switchUser(switcher.value));
  document.getElementById("share-button").addEventListener("click", openShareModal);
  document.getElementById("close-share").addEventListener("click", () => { modal.hidden = true; });
  modal.addEventListener("click", (event) => { if (event.target === modal) modal.hidden = true; });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") modal.hidden = true; });

  titleInput.addEventListener("input", () => {
    if (!activeDocument) return;
    const documentId = activeDocument.id;
    const title = titleInput.value;
    clearTimeout(titleSaveTimer);
    setSaveState("saving", "Unsaved changes");
    titleSaveTimer = setTimeout(() => saveDocument({ title }, documentId), 500);
  });
  titleInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") titleInput.blur();
  });

  document.getElementById("share-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    shareError.textContent = "";
    try {
      await api(`/api/documents/${activeDocument.id}/shares`, {
        method: "POST",
        body: JSON.stringify({ email: shareSelect.value }),
      });
      await refreshShares();
      showToast("Document shared");
    } catch (error) {
      shareError.textContent = error.message;
    }
  });

  document.getElementById("file-upload").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const extension = file.name.split(".").pop().toLowerCase();
    if (!["txt", "md"].includes(extension)) {
      showToast("Please choose a .txt or .md file.");
      event.target.value = "";
      return;
    }
    try {
      const form = new FormData();
      form.append("file", file);
      if (extension === "md") {
        const markdown = await file.text();
        form.append("rendered_content", window.marked.parse(markdown));
      }
      const { document: doc } = await api("/api/documents/import", { method: "POST", body: form });
      await refreshDocuments();
      await openDocument(doc.id);
      showToast("File imported successfully");
    } catch (error) {
      showToast(error.message);
    } finally {
      event.target.value = "";
    }
  });

  quill = new Quill("#editor", {
    theme: "snow",
    placeholder: "Start writing your thoughts…",
    modules: { toolbar: "#toolbar-container" },
  });
  quill.on("text-change", scheduleContentSave);

  api("/api/session").then(async (data) => {
    const initialUser = data.user_email || users[0];
    switcher.value = initialUser;
    await switchUser(initialUser);
  }).catch((error) => showToast(error.message));
})();
