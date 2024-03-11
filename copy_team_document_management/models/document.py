import os
import shutil
import tempfile
from datetime import datetime
import base64
import pytz
from odoo import fields, models, api
from odoo.exceptions import UserError


class DocumentDocument(models.Model):
    _name = 'document.document'
    _rec_name = 'directory_name'
    _description = 'Folder'
    _inherit = ['mail.thread']
    _order = 'sequence,id'

    sequence = fields.Integer(default=1, help="Gives the sequence order when displaying a list of records.")

    directory_name = fields.Char(string='Name', required=True)
    created_by = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, readonly=True,
                                 store=True)
    description = fields.Char(string='Description')
    # department = fields.Char(string='Owner Department', default=lambda self: self.env.user.department_id.name,
    #                          readonly=True, required=True)
    department = fields.Char(string='Owner Department', default=lambda self: self.env.user.department_id.name,
                             readonly=True)
    dept_tag_ids = fields.Many2many('hr.department', string='Department Tags', store=True)
    dept_tag_names = fields.Char(compute='_compute_dept_tag_names', store=True)
    user_tag_ids = fields.Many2many('res.users', string='User Tags', store=True)
    user_tag_names = fields.Char(compute='_compute_user_tag_names', store=True)
    access_mode = fields.Selection(
        [('public', 'Public'), ('private', 'Private')],
        string='Access Mode',
        default='private',
        required=True,
    )
    file_count = fields.Integer(string='File Count', compute='_compute_file_count', store=True)
    file_upload_line_ids = fields.One2many('document.file.upload.line', 'document_id', string='File Upload Lines')

    @api.depends('file_upload_line_ids')
    def _compute_file_count(self):
        for document in self:
            document.file_count = len(document.file_upload_line_ids.filtered(lambda f: f.document_id == document))

    @api.depends('dept_tag_ids')
    def _compute_dept_tag_names(self):
        for rec in self:
            dept_tag_names = ", ".join(tag.name for tag in rec.dept_tag_ids)
            rec.dept_tag_names = dept_tag_names

    @api.depends('user_tag_ids')
    def _compute_user_tag_names(self):
        for rec in self:
            user_tag_names = ", ".join(tag.name for tag in rec.user_tag_ids)
            rec.user_tag_names = user_tag_names

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user and self.env.user.id:
            user_id = self.env.user.id

            args = ['|', '&', ('created_by', '=', user_id), ('access_mode', '=', 'private'),
                    ('access_mode', '=', 'public')] + args

            # Include documents created by the current user and public documents.
        return super(DocumentDocument, self).search(args, offset, limit, order, count)

    @api.model
    def create(self, vals):

        # Check if a directory with the same name already exists
        existing_directory = self.search([('directory_name', '=', vals['directory_name'])])
        if existing_directory:
            raise UserError("Directory with the same name already exists.")

        if vals.get('access_mode') == 'private':
            vals['created_by'] = self.env.user.id  # Set the owner to the current user

        record = super(DocumentDocument, self).create(vals)
        return record


class DocumentFileUploadLine(models.Model):
    _name = 'document.file.upload.line'
    _rec_name = 'file_name'
    _description = 'File'

    document_id = fields.Many2one('document.document', string='Document')
    directory_name = fields.Char(related='document_id.directory_name', store=True)
    file_name = fields.Char(string='File Name', required=True)
    file_upload = fields.Binary(string='Upload File', required=True, attachment=True, store=True)
    file_url = fields.Char(string='File URL', readonly=True)
    file_path = fields.Char(string='File Path')
    file_copy = fields.Char(string='Copy File')

    last_activity = fields.Char(string="Last activity Info", compute="_compute_combined_field", store=True,
                                readonly=True)

    binary_raw = fields.Text(string="File Binary", compute='get_binary', store=True)

    def create(self, vals):
        records = super(DocumentFileUploadLine, self).create(vals)
        for record in records:
            if record.file_upload and record.file_name:
                # Perform actions for each record
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file.write(base64.b64decode(record.file_upload))
                temp_file.close()
                file_url = f"{base_url}/web/content/{record._name}/{record.id}/file_upload/{record.file_name}"
                record.file_copy = file_url
                relative_path = os.path.join(
                    'team_document_management/static/repository',
                    record.document_id.department,
                    record.document_id.created_by.name,
                    record.document_id.directory_name,
                    record.file_name
                )
                record.write({'file_path': relative_path})
        return records

    # def unlink(self):
    #     for record in self:
    #         # Create a record in deleted.file model before deletion
    #         self.env['deleted.file'].create({
    #             'document_line_id': record.id,
    #             'file_name': record.file_name,
    #             'file_upload': record.file_upload,
    #         })
    #     return super(DocumentFileUploadLine, self).unlink()

    @api.onchange('file_upload')
    def get_binary(self):
        # file = False
        # binary = self.env["ir.attachment"].sudo().search([("res_model", "=", "document.file.upload.line"),("res_id", "=", self.id),("res_field", "=", "file_upload")],limit=1,).datas
        # print(binary)
        # if binary:
        #     file = base64.b64decode(binary)
        #     print("File: ", file)
        #
        # self.binary_raw = file

        for rec in self:
            file = False
            binary = self.env["ir.attachment"].sudo().search(
                [("res_model", "=", "document.file.upload.line"), ("res_id", "=", rec.id),
                 ("res_field", "=", "file_upload"), ], limit=1)
            # print(binary)
            # print("Binary", binary)
            if binary:
                path = binary.store_fname
                print("PATH", path)
                file_datas = binary._file_read(fname=binary.store_fname)
                # print('file_datas', file_datas)
                rec.binary_raw = file_datas

            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'document.file.upload.line'),
                ('res_id', '=', rec.id),
                ('res_field', '=', 'file_upload'),
            ], limit=1)

            if attachment:
                checksum = attachment.checksum
                print(f"Checksum for the attachment: {checksum}")
                name = str(attachment.name)
                print(f"attachment: {name}")

                checksum = self.file_name
                print(f"New: {checksum}")

    @api.depends('write_uid', 'write_date')
    def _compute_combined_field(self):
        for rec in self:
            combined_info = f"{rec.write_uid.display_name} at {rec.write_date}"
            # print(combined_info)
            rec.last_activity = combined_info

    def preview_file(self):
        # Create a temporary file to store the binary content
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(base64.b64decode(self.file_upload))
        temp_file.close()

        # Define the URL for the temporary file to be opened in a new tab
        file_url = f"/web/content/{self._name}/{self.id}/file_upload/{self.file_name}"

        self.write({'file_url': file_url})

        # Open a new tab for the file preview
        for rec in self:
            return {
                'type': 'ir.actions.act_url',
                'url': file_url,
                'target': 'new',
            }


class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=', vals.get('res_model')),
                                                      ('res_id', '=', vals.get('res_id')),
                                                      ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        return super(Followers, self).create(vals)

# class DeletedFile(models.Model):
#     _name = 'deleted.file'
#     _description = 'Deleted Files'
#
#     document_line_id = fields.Many2one('document.file.upload.line', string='Original File')
#     file_name = fields.Char(string='File Name', related='document_line_id.file_name')
#     file_upload = fields.Binary(string='Upload File', related='document_line_id.file_upload')
#
#     @api.model
#     def _get_deleted_files(self):
#         """Get only the deleted files."""
#         print("SAVE DELETED FILES")
#         return self.search([('active', '=', False)])
#
#     def action_view_deleted_files(self):
#         """Action to view deleted files."""
#         deleted_files = self._get_deleted_files()
#         action = self.env.ref('team_document_management.action_deleted_file_list').read()[0]
#         action['domain'] = [('id', 'in', deleted_files.ids)]
#         return action
