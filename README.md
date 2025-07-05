# ControlDesk

**ControlDesk** é uma plataforma de gerenciamento de despesas que ajuda empresas e equipes a controlar seus gastos de forma eficiente. O aplicativo é composto por um frontend em **React Native** e um backend em **Flask**, utilizando **PostgreSQL** como banco de dados hospedado na **BRdrive**.

## Funcionalidades

- **Cadastro de Despesas**: Adicione novas despesas com informações detalhadas como cidade, nome do estabelecimento, CPF/CNPJ, tipo de despesa, valor e anexe comprovantes.
- **Histórico de Despesas**: Consulte um histórico detalhado de todas as despesas cadastradas, com opções de filtro por projeto e data.
- **Upload de Comprovantes**: Anexe imagens de comprovantes de despesas diretamente pelo app.
- **Relatórios Mensais**: A gestão da empresa poderá acessar um site web vinculado ao sistema, onde será possível visualizar e gerar relatórios mensais de gastos.
- **Cadastro de Colaboradores, empresas e Projetos**: Somente a gestão da empresa terá permissões especiais no site web para cadastrar novos colaboradores, novas filiais e novos projetos. Os projetos são apontados para filiais e colaboradores específicos.

## Tecnologias Utilizadas

- **Frontend**: CSS e JavaScript
- **Backend**: Flask
- **Banco de Dados**: PostgreSQL (hospedado na **BRdrive**)
- **Autenticação**: JWT e OAuth2

