#!/usr/bin/perl
# Author: Petr Vileta, 2012
# License: WTFPL - Do What The Fuck You Want To Public License, http://sam.zoy.org/wtfpl/
use strict;
1;


sub connect_db
{
#############################################
# nastavit dle potreby
my $db='pirati';
my $dbhost='localhost';
my $dbport='3308';
my $dbuser='nejaky_uzivatel';
my $dbpw='nejake_heslo';
my $ruononserver=1; # pokud bezi na serveru PS 1, pro testovani apod. 0
#############################################
return ($db,$dbhost,$dbport,$dbuser,$dbpw,$ruononserver);
}

sub get_setup
{
use vars qw/$dbh/;
my ($name,$field)=@_;
my $ret;
my $sth=$dbh->prepare("select `$field` from `evidence_setup` where `name`=?");
$sth->execute($name) or die $sth->errstr;
if($sth->rows)
	{
	($ret)=$sth->fetchrow_array();
	}
$sth->finish;
return $ret;
}

sub log_it
{
my ($admin,$for,$txt)=@_;
$admin*=1;
$for*=1;
my $sth;
if($for > 0 and ($txt=~s/#/#/sg)==1)
	{
	$sth=$dbh->prepare("SELECT `username_clean` FROM `phpbb_users` WHERE `user_id`=?");
	$sth->execute($for); # or die $sth->errstr;
	if($sth->rows)
		{
		my ($name)=$sth->fetchrow_array;
		$txt=~s/#/$name/s;
		}
	else
		{
		$txt=~s/#/$for/s;
		}
	}
$sth=$dbh->prepare("INSERT INTO `evidence_log` SET
		`provedl`=?,`pro_koho`=?,`popis`=?");
$sth->execute($admin,$for,$txt); # or die $sth->errstr;
$sth->finish;
}
