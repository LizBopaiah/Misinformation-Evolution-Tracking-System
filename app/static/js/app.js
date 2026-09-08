// Misinformation Detection and Evolution Tracking System (MET) Frontend Engine

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Dark Mode Theme Configuration
    initTheme();

    // 2. Initialize Mobile Navigation Listeners
    initMobileNav();
});

/**
 * Handles Light/Dark Theme Initialization and Toggling
 */
function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;

    // Determine default theme
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }

    // Toggle event listener
    themeToggleBtn.addEventListener('click', () => {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        }
    });
}

/**
 * Handles sidebar drawer toggling on mobile viewports
 */
function initMobileNav() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar-panel');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('-translate-x-full');
        });
    }
}

/**
 * UI Component: Toast Notifications Manager
 */
const Toast = {
    containerId: 'toast-container',

    getContainer() {
        let container = document.getElementById(this.containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-3 max-w-sm w-full px-4';
            document.body.appendChild(container);
        }
        return container;
    },

    show(message, type = 'info', duration = 4000) {
        const container = this.getContainer();
        const toast = document.createElement('div');
        
        // Setup icons and colors
        let typeClasses = 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200';
        let icon = `<svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;

        if (type === 'success') {
            typeClasses = 'bg-white dark:bg-slate-900 border-emerald-100 dark:border-emerald-950 text-slate-800 dark:text-slate-200';
            icon = `<svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
        } else if (type === 'error') {
            typeClasses = 'bg-white dark:bg-slate-900 border-rose-100 dark:border-rose-950 text-slate-800 dark:text-slate-200';
            icon = `<svg class="w-5 h-5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
        } else if (type === 'warning') {
            typeClasses = 'bg-white dark:bg-slate-900 border-amber-100 dark:border-amber-950 text-slate-800 dark:text-slate-200';
            icon = `<svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>`;
        }

        toast.className = `flex items-start gap-3 p-4 rounded-xl border shadow-lg transform translate-y-2 opacity-0 transition-all duration-300 ${typeClasses}`;
        toast.innerHTML = `
            <div class="flex-shrink-0 mt-0.5">${icon}</div>
            <div class="flex-grow text-sm font-medium leading-5">${message}</div>
            <button onclick="this.parentElement.remove()" class="flex-shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        `;

        container.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-y-2', 'opacity-0');
        }, 10);

        // Animate out and remove
        setTimeout(() => {
            toast.classList.add('translate-y-2', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

/**
 * UI Component: Modals Manager
 */
const Modal = {
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.classList.add('overflow-hidden');
        }
    },
    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.classList.remove('overflow-hidden');
        }
    }
};

/**
 * UI Component: Loader Control
 */
const Loader = {
    show(targetId = 'global-loader') {
        const loader = document.getElementById(targetId);
        if (loader) {
            loader.classList.remove('hidden');
        }
    },
    hide(targetId = 'global-loader') {
        const loader = document.getElementById(targetId);
        if (loader) {
            loader.classList.add('hidden');
        }
    }
};

/**
 * UI Component: Universal File Downloader & Local Disk Saver
 */
const DownloadManager = {
    async download(url, filename) {
        const token = localStorage.getItem('access_token');
        let ext = 'pdf';
        let mimeType = 'application/pdf';
        let desc = 'PDF Document';

        if (filename.endsWith('.png')) {
            ext = 'png';
            mimeType = 'image/png';
            desc = 'PNG Image';
        } else if (filename.endsWith('.jpg') || filename.endsWith('.jpeg')) {
            ext = 'jpg';
            mimeType = 'image/jpeg';
            desc = 'JPEG Image';
        }

        Loader.show();
        try {
            const separator = url.includes('?') ? '&' : '?';
            const authUrl = token ? `${url}${separator}token=${encodeURIComponent(token)}` : url;
            
            const response = await fetch(authUrl, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const blob = await response.blob();
            Loader.hide();

            // 1. Try modern File System Access API (Prompts native Windows 'Save As' file dialog)
            if (window.showSaveFilePicker) {
                try {
                    const acceptMap = {};
                    acceptMap[mimeType] = [`.${ext}`];
                    const handle = await window.showSaveFilePicker({
                        suggestedName: filename,
                        types: [{
                            description: desc,
                            accept: acceptMap
                        }]
                    });
                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    Toast.show(`Saved ${filename} directly to your selected folder!`, "success");
                    return;
                } catch (pickerErr) {
                    if (pickerErr.name === 'AbortError') {
                        Toast.show("Save cancelled.", "info");
                        return;
                    }
                }
            }

            // 2. Standard Blob download fallback
            const fileBlob = new Blob([blob], { type: mimeType });
            const blobUrl = window.URL.createObjectURL(fileBlob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                window.URL.revokeObjectURL(blobUrl);
                if (a.parentNode) a.parentNode.removeChild(a);
            }, 4000);
            Toast.show(`Saved ${filename} to your Downloads folder!`, "success");
        } catch (err) {
            Loader.hide();
            console.error("Download manager error:", err);
            const separator = url.includes('?') ? '&' : '?';
            const authUrl = token ? `${url}${separator}token=${encodeURIComponent(token)}` : url;
            window.location.href = authUrl;
        }
    }
};
