// @ts-check
import { defineConfig } from 'astro/config';
import { satteri } from '@astrojs/markdown-satteri';
import { createCssVariablesTheme } from 'shiki';
import { ancorasNosTitulos } from './src/plugins/ancoras-nos-titulos.mjs';
import { baseNosLinks } from './src/plugins/base-nos-links.mjs';
import { tabelasRolaveis } from './src/plugins/tabelas-rolaveis.mjs';

// Publicado no GitHub Pages em https://filipegh03.github.io/forge/ (D8).
const site = 'https://filipegh03.github.io';
const base = '/forge';

export default defineConfig({
  site,
  base,
  output: 'static',
  markdown: {
    // O conteúdo escreve os links internos sem o base (contrato 1.1);
    // o prefixo entra aqui, no build. Os ## e ### ganham o link direto da seção.
    processor: satteri({ hastPlugins: [baseNosLinks(base), tabelasRolaveis(), ancorasNosTitulos()] }),
    // As cores do código vêm das variáveis --codigo-* do src/estilos/global.css,
    // que seguem a paleta e o claro/escuro do site (DESIGN.md).
    shikiConfig: { theme: createCssVariablesTheme({ name: 'forge', variablePrefix: '--codigo-' }) },
  },
});
