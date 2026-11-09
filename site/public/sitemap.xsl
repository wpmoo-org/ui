<?xml version="1.0" encoding="UTF-8"?>
<!--
  Presents sitemap.xml to people who open it in a browser. Search engines read
  the XML itself and ignore this stylesheet. The page reuses the published
  Moo UI stylesheet and theme bootstrap, so it follows the catalog's light or
  dark preference. Browsers without XSLT show the plain XML instead.
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
  exclude-result-prefixes="sitemap">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <xsl:text disable-output-escaping="yes">&lt;!doctype html&gt;</xsl:text>
    <html lang="en" dir="ltr">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta name="robots" content="noindex, follow"/>
        <title>XML Sitemap — Moo UI</title>
        <link rel="icon" type="image/svg+xml" href="favicon.svg"/>
        <link rel="stylesheet" href="assets/css/moo-ui.min.css"/>
      </head>
      <body>
        <div class="moo-ui" data-bs-theme="light" data-moo-document-owner="true">
          <script src="assets/js/state.js"></script>
          <main class="container py-5">
            <div class="row justify-content-center">
              <div class="col-12 col-lg-10 col-xl-8">
                <h1 class="h2 mb-2">XML Sitemap</h1>
                <p class="text-body-secondary mb-4">
                  This XML sitemap lists the
                  <strong><xsl:value-of select="count(sitemap:urlset/sitemap:url)"/></strong>
                  public URLs of the Moo UI catalog for search engines such as Google and Bing.
                  It follows the
                  <a href="https://www.sitemaps.org/protocol.html" target="_blank" rel="noopener noreferrer">sitemaps.org protocol</a>.
                  For a version grouped by section with page descriptions, open the
                  <a href="sitemap/">Sitemap page</a>.
                </p>
                <div class="table-responsive">
                  <table class="table">
                    <thead>
                      <tr>
                        <th scope="col" class="text-end">#</th>
                        <th scope="col">URL</th>
                        <th scope="col" class="text-end">Last modified</th>
                      </tr>
                    </thead>
                    <tbody>
                      <xsl:for-each select="sitemap:urlset/sitemap:url">
                        <tr>
                          <td class="text-end text-body-secondary"><xsl:value-of select="position()"/></td>
                          <td class="text-break">
                            <a href="{sitemap:loc}"><xsl:value-of select="sitemap:loc"/></a>
                          </td>
                          <td class="text-end text-nowrap">
                            <xsl:choose>
                              <xsl:when test="sitemap:lastmod"><xsl:value-of select="sitemap:lastmod"/></xsl:when>
                              <xsl:otherwise><span class="text-body-secondary">—</span></xsl:otherwise>
                            </xsl:choose>
                          </td>
                        </tr>
                      </xsl:for-each>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </main>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
