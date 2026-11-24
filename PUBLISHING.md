# Publishing this repository on GitHub / HACS / Marketplace

This file is for the maintainer. The integration code is already populated; **do not replace it with your laptop's `.venv`, cloud responses, or Home Assistant `.storage`**.

## 1. Prepare the GitHub metadata

Choose the public GitHub repository name `ha-broadlink-cloud` (or your own name). From the **project root**, run:

```powershell
python setup_github.py --owner YOUR_GITHUB_USERNAME --repo ha-broadlink-cloud
```

This fills in the correct `documentation`, `issue_tracker`, `codeowners` and README links. Review all files and make sure `pretendor` and `ha-broadlink-cloud` no longer appear in the manifest or README.

## 2. Create your repository

On GitHub, create a **public**, empty repository with your chosen name. **Do not** create a GitHub README or license in the empty repository: they already exist locally. Keep **Issues enabled** and add a short description and topics (e.g. `home-assistant`, `broadlink`, `hacs`, `marketplace`, `custom-integration`).

Commit and push the *contents* of this folder, keeping `.github/`, `custom_components/`, `tests/`, `hacs.json`, etc. at repository root. Use GitHub Desktop or PowerShell; `publish-github.ps1` can automate the git steps once the empty remote repository exists.

## 3. Verify GitHub Actions

Open your repository's **Actions** tab. Wait for the **Offline tests**, **HACS validation**, and **Hassfest** jobs. They must pass. Fix errors before release (do not disable HACS checks). Note: Local unit tests do not replace these checks or real user testing.

## 4. Create your first published release

In GitHub open **Releases → Draft a new release**. Create tag **`0.1.2`** from `main` and title **`0.1.2`**. Publish the release (a tag alone is not enough). The tag's version matches `manifest.json` (`0.1.2`). No ZIP asset is required: Marketplace/HACS installs from `custom_components/broadlink_cloud/`.

Suggested release notes: "First public preview. Unofficial EU BroadLink Cloud login, IR/RF single-code command discovery and button control. Tested on one RM Pro+. No device state feedback, no multi-hub routing."

## 5. Test installation using a custom repository link

In Home Assistant 2026.11+ open **Settings → Marketplace → Custom repositories** (or the [My Home Assistant repository link](https://my.home-assistant.io/redirect/hacs_repository/?owner=pretendor&repository=ha-broadlink-cloud&category=integration)). Enter your public GitHub repository URL and select **Integration**. In older Home Assistant, use HACS **Custom repositories**.

Test on a clean Home Assistant instance if possible, not only your existing manually installed integration. Install, restart if prompted, sign in, and test exactly one safe command. Existing manually installed users should back up the integration's configuration and verify the update does not replace their config entry.

## 6. Get it listed in the public catalog

Once both validation Actions are passing and the GitHub release is published, fork [hacs/default](https://github.com/hacs/default) into your **personal GitHub account**, branch from `master`, and add `pretendor/ha-broadlink-cloud` (matching your actual repository) alphabetically to the `integration` JSON list. Submit a pull request using the provided template. **Approval is not automatic; it can take months.** Meanwhile anyone can add the repository using its URL.

Official guidance:
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/guides/catalog/
- https://contributors.home-assistant.io/marketplace/reference/validation/
- https://contributors.home-assistant.io/marketplace/guides/releases/
